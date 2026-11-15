"""Turn Jaeger UI JSON exports into a timing report (no running SDK required)."""

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
import json
from pathlib import Path


DESCRIPTIONS = {
    "dialbb.process": "対話処理全体",
    "dialbb.block": "設定ブロックの実行",
    "dialogue.call_process": "ワーカから DialBB ライブラリの呼び出しと応答まで",
    "llm_dialogue.generate_utterance": "LLM による応答文生成",
    "dialbb.request": "DialBB worker の要求処理",
    "dialogue.turn": "入力音声の受信から最後の応答音声の送信完了まで",
    "tts.request": "TTS 要求全体（途中セグメントの再生待ちを含む）",
    "tts.synthesize": "音声合成 API 呼び出し",
    "tts.send_and_playback": "音声送信と再生完了待ち（ターン終了まで）",
    "tts.playback_wait": "ブラウザの再生完了 ACK 待ち",
    "stt.utterance": "入力音声の受信から確定認識まで",
    "stt.transcription_wait": "発話終了通知から確定認識までの待ち",
    "llm.invoke": "LLM API 呼び出し（リトライは個別に計測）",
    "dst.format_history": "対話履歴の文字列化",
    "dst.extract_slots": "スロット抽出全体",
    "dst.parse_result": "LLM 応答の JSON 解析",
    "stn.transition": "遷移先探索とアクション",
    "stn.check_condition": "遷移条件の評価",
    "stn.perform_actions": "アクション列の実行",
    "stn.generate_utterance": "システム発話の変数・関数展開",
    "stn.generate_confirmation": "確認要求の生成",
    "browser.schedule_wait": "イベントループへの投入待ち",
    "browser.send": "WebSocket 送信",
}


@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start: int
    duration: int
    service: str
    block: str
    parent: tuple[str, str] | None
    children: list = field(default_factory=list, compare=False)

    @property
    def key(self):
        return self.service, self.name, self.block

    @property
    def self_time(self):
        """Subtract the union of direct children, clipped to this span's interval."""
        end = self.start + self.duration
        intervals = sorted((max(self.start, child.start),
                            min(end, child.start + child.duration))
                           for child in self.children)
        covered = 0
        cursor = self.start
        for start, stop in intervals:
            covered += max(0, stop - max(cursor, start))
            cursor = max(cursor, stop)
        return self.duration - covered


def load_spans(paths):
    """Read Jaeger {data: [trace]} exports; repeated exports are deduplicated."""
    spans = {}
    warnings = set()
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError(f"{path}: Jaeger JSON の data 配列が必要です")
        if payload.get("errors"):
            raise ValueError(f"{path}: Jaeger がエラーを返しています: {payload['errors']}")
        try:
            for item in payload["data"]:
                for message in item.get("warnings") or []:
                    warnings.add(str(message))
                for raw in item["spans"]:
                    trace_id = raw.get("traceID", item["traceID"])
                    start, duration = raw["startTime"], raw["duration"]
                    if (type(start) is not int or type(duration) is not int
                            or start < 0 or duration < 0):
                        raise ValueError("startTime と duration は非負整数（µs）が必要です")
                    tags = {tag["key"]: tag["value"] for tag in raw.get("tags") or []}
                    parents = [(ref["traceID"], ref["spanID"])
                               for ref in raw.get("references") or []
                               if ref["refType"] == "CHILD_OF"]
                    if not parents and raw.get("parentSpanID"):
                        parents = [(trace_id, raw["parentSpanID"])]
                    if len(set(parents)) > 1:
                        raise ValueError("複数の CHILD_OF 親は集計できません")
                    process = (item.get("processes") or {}).get(raw.get("processID"), {})
                    process = raw.get("process") or process
                    span = Span(trace_id, raw["spanID"], raw["operationName"],
                                start, duration, process.get("serviceName", "unknown"),
                                str(tags.get("block.name", "")), parents[0] if parents else None)
                    key = trace_id, span.span_id
                    if key in spans and spans[key] != span:
                        raise ValueError(f"同じ span に異なるデータがあります: {key}")
                    spans[key] = span
                    for message in raw.get("warnings") or []:
                        warnings.add(str(message))
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError(f"{path}: Jaeger の trace/span 形式が不正です") from exc

    if not spans:
        raise ValueError("集計できる span がありません")
    # Validate before linking so cycles cannot cause recursive traversal to hang.
    checked = set()
    for key in spans:
        chain = set()
        current = key
        while current in spans and current not in checked:
            if current in chain:
                raise ValueError("span の親子関係が循環しています")
            chain.add(current)
            current = spans[current].parent
        checked.update(chain)
    for span in spans.values():
        if span.parent in spans:
            parent = spans[span.parent]
            parent.children.append(span)
            if (span.start < parent.start or
                    span.start + span.duration > parent.start + parent.duration):
                warnings.add("親の時間区間外の子 span があります。自己時間は親の区間に切り詰めて計算します。")
        elif span.parent:
            warnings.add("親 span が不足しています。欠けた親を持つ span は独立したルートとして表示します。")
    return list(spans.values()), sorted(warnings)


def format_time(microseconds):
    if microseconds >= 1_000_000:
        return f"{microseconds / 1_000_000:.3f}".rstrip("0").rstrip(".") + "s"
    if microseconds >= 1000:
        return f"{microseconds / 1000:.3f}".rstrip("0").rstrip(".") + "ms"
    return f"{microseconds:g}µs"


def label(key):
    service, name, block = key
    return f"{service} / {name}" + (f" (block={block})" if block else "")


def markdown(text):
    return str(text).replace("\n", " ").replace("\r", " ").replace("|", "\\|").replace("`", "'")


def description(name):
    if name.endswith(".queue_wait"):
        return "キュー投入から処理開始までの待ち"
    if name.startswith("stn.scenario_function."):
        return "シナリオ関数の実行"
    return DESCRIPTIONS.get(name, "")


def make_report(spans, warnings=(), root_name=None, *, details=False):
    all_keys = {(span.trace_id, span.span_id) for span in spans}
    roots = [span for span in spans if span.parent not in all_keys]
    if root_name:
        # Select the outermost occurrence so recursive operations are not counted twice.
        roots = []
        lookup = {(span.trace_id, span.span_id): span for span in spans}
        for span in spans:
            if span.name != root_name:
                continue
            parent = lookup.get(span.parent)
            while parent is not None and parent.name != root_name:
                parent = lookup.get(parent.parent)
            if parent is None:
                roots.append(span)
    if not roots:
        raise ValueError(f"対象のルート span がありません: {root_name}")
    roots.sort(key=lambda span: (span.start, span.trace_id, span.span_id))
    lines = ["# 処理時間レポート", "",
             f"対象: {len(roots)}件（{len({s.trace_id for s in roots})}トレース）", "",
             "全体の時間には、下に並ぶ処理の時間が含まれます。", ""]
    if details:
        lines.extend([
            "自己時間は、その処理の時間から子の処理にかかった時間を除いたものです。",
            "同時に動いた子の時間は重複して差し引きません。自己時間には待機や未計測の処理も含みます。",
            "親子の値は加算できません。同時実行や再帰呼び出しがあると、子の合計が親を超える場合があります。",
            "別トレースへのリンクは親子として合算しません。", ""])
    for warning in warnings:
        lines.extend([f"> 注意: {markdown(warning)}", ""])
    totals = defaultdict(list)
    multiple_services = len({span.service for span in spans}) > 1

    def display_label(key):
        if details or multiple_services:
            return label(key)
        _, name, block = key
        return name + (f" (block={block})" if block else "")

    def render_group(group, depth):
        grouped = defaultdict(list)
        for span in group:
            grouped[span.key].append(span)
            totals[span.key].append(span)
        for key, members in sorted(grouped.items(),
                                   key=lambda item: (-sum(s.duration for s in item[1]), item[0])):
            duration = sum(s.duration for s in members)
            detail = description(key[1])
            suffix = f"（{len(members)}回"
            if details:
                suffix += f"、自己時間 {format_time(sum(s.self_time for s in members))}"
            suffix += "）"
            lines.append(f"{'    ' * depth}- {markdown(display_label(key))} [{format_time(duration)}]"
                         f"{' …' + detail if detail else ''}{suffix}")
            render_group([child for span in members for child in span.children], depth + 1)

    if not details:
        render_group(roots, 0)
        lines.append("")
    else:
        for root in roots:
            lines.extend([f"## trace {markdown(root.trace_id)} / span {markdown(root.span_id)}", ""])
            render_group([root], 0)
            lines.append("")
    if details:
        lines.extend(["## 処理別集計（自己時間の累計が長い順）", "",
                  f"対象: {len(roots)}ルート / {len({s.trace_id for s in roots})}トレース。平均・最大は span 1回あたり。",
                  "この表の全行を足しても、全体の経過時間にはなりません。", "",
                  "| 処理 | 回数 | 累計（子を含む） | 自己時間の累計 | 平均 | 最大 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: |"])
    else:
        lines.extend(["## 処理別集計（合計時間が長い順）", "",
                      "平均・最大は処理1回あたりの時間です。", "",
                      "| 処理 | 回数 | 合計 | 平均 | 最大 |",
                      "| --- | ---: | ---: | ---: | ---: |"])
    for key, members in sorted(totals.items(),
                               key=lambda item: (-sum(s.self_time if details else s.duration
                                                      for s in item[1]), item[0])):
        total = sum(s.duration for s in members)
        self_column = f"{format_time(sum(s.self_time for s in members))} | " if details else ""
        lines.append(f"| {markdown(display_label(key))} | {len(members)} | {format_time(total)} | "
                     f"{self_column}"
                     f"{format_time(total / len(members))} | {format_time(max(s.duration for s in members))} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", help="Jaeger UI の JSON エクスポート（複数指定可）")
    parser.add_argument("--root", help="内訳を表示する Operation（例: dialbb.process / tts.request）")
    parser.add_argument("--details", action="store_true", help="トレースごとの内訳・自己時間も表示")
    parser.add_argument("-o", "--output", type=Path, help="Markdown の出力先（省略時は標準出力）")
    args = parser.parse_args()
    try:
        spans, warnings = load_spans(args.files)
        report = make_report(spans, warnings, args.root, details=args.details)
        if args.output:
            args.output.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
    except (OSError, ValueError, RecursionError) as exc:
        parser.exit(2, f"trace-report: {exc}\n")


if __name__ == "__main__":
    main()
