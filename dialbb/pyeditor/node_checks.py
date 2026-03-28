import json
import re

from dialbb.no_code.gui_utils import gui_text


# 正規表現パターン（scenario JSON 内の条件検査で使用）
llm_pattern = re.compile(r'\$".*?"')
llm_pattern2 = re.compile(r"\$.*?\$")
prompt_template_pattern = re.compile(r"\$\$\$.*?\$\$\$", re.DOTALL)
str_eq_pattern = re.compile(r"(.+?)\s*==\s*(.+)")
str_ne_pattern = re.compile(r"(.+?)\s*!=\s*(.+)")
num_turns_exceeds_pattern = re.compile(r'_num_turns_exceeds\(\s*"\d+"\s*\)')
num_turns_in_state_exceeds_pattern = re.compile(
    r'_num_turns_in_state_exceeds\(\s*"\d+"\s*\)'
)
num_turns_exceeds_pattern2 = re.compile(r"TT\s*[>]\s*(\d+)")
num_turns_in_state_exceeds_pattern2 = re.compile(r"TS\s*[>＞]\s*(\d+)")


def illegal_condition(condition: str) -> bool:
    """
    条件文字列の妥当性を判定する。

    受け取る `condition` は事前にトリムされ、セミコロンで分割された単一条件を想定する。
    次のいずれかの形式に完全一致（fullmatch）する場合は「許容される条件」とみなし
    関数は False を返す。どれにも一致しない場合は True を返し“不正（illegal）”と判断する。

    許容される形式（正規表現、コード上の変数名）:
    - LLM 式（例: $"..."）: `llm_pattern`
    - LLM 式（代替、$...$）: `llm_pattern2`
    - プロンプトテンプレート（$$$ ... $$$、改行含む可）: `prompt_template_pattern`
    - 文字列等価比較（a == b）: `str_eq_pattern`
    - 文字列不等比較（a != b）: `str_ne_pattern`
    - ターン数超過チェック（関数形式 _num_turns_exceeds("N"））: `num_turns_exceeds_pattern`
    - ステート内ターン数超過（関数形式 _num_turns_in_state_exceeds("N"））: `num_turns_in_state_exceeds_pattern`
    - ターン数超過（短縮表記 TT > N）: `num_turns_exceeds_pattern2`
    - ステート内ターン数超過（短縮表記 TS > N、全角含む）: `num_turns_in_state_exceeds_pattern2`

    戻り値:
    - True: 不正な条件（警告対象）
    - False: 許容される条件
    """

    if(
        llm_pattern.fullmatch(condition)
        or llm_pattern2.fullmatch(condition)
        or prompt_template_pattern.fullmatch(condition)
        or str_eq_pattern.fullmatch(condition)
        or str_ne_pattern.fullmatch(condition)
        or num_turns_exceeds_pattern.fullmatch(condition)
        or num_turns_exceeds_pattern2.fullmatch(condition)
        or num_turns_in_state_exceeds_pattern.fullmatch(condition)
        or num_turns_in_state_exceeds_pattern2.fullmatch(condition)
    ):
        return False
    else:
        return True


def node_check_and_warn(node_data: dict) -> str:
    """
    シナリオJSONファイルを読み込み、簡易的な妥当性／論理チェックを行い警告文字列を返す。

    実施するチェック項目:
    1. ノードIDが空ならエラー
    2. ユーザーノード:
        1) どこにもコネクター接続されていない(遷移先がない)ノードはエラー
        2) `conditions` をillegal_condition()で判定。NGならばエラー
        3) `actions` が空でなければエラー
        - ノードIDが `connect_sources` に含まれなければ `msg_warn_user_node_no_transition_dest` を追加。
    3. システムノード:
                - `type` が空ならエラー
                - 'initial'ノードが存在しなければエラー
                - 'error'ノードが存在しなければエラー
                - `utterance` が空ならエラー

    出力:
    - すべての警告メッセージを改行で連結した文字列を返す。警告がなければ空文字列を返す。

    注意:
    - JSON のパースエラーは現在ハンドルされない（例外が上がる）。
    - メッセージは `gui_text()` のキー（ローカライズ済み文言）を使用して生成される。
    """

    warning: str = ""
    initial_node_exists: bool = False
    error_node_exists: bool = False

    # connect_sources：GraphScene の export 形式では edges[].from が source
    connect_sources = []
    for e in node_data.get("edges", []):
        # old no-code 形式の 'connects' にも対応
        if isinstance(e, dict) and "from" in e:
            connect_sources.append(e.get("from"))

    for node in node_data.get("nodes", []):
        node_id: str = node.get("id", "")
        short_id: str = node.get("short_id", "")

        # 判別: GraphScene 形式では 'type' フィールドに NODE_TYPE_* が入る
        ntype = node.get("type", "")

        # ユーザノード判定（GraphScene の 'type' を参照）
        is_user = bool(ntype and str(ntype).lower().startswith("user"))

        if is_user:
            # 条件（GraphScene 形式の 'condition' フィールド）
            conditions = str(node.get("condition", "")).strip()
            if conditions != "":
                for condition in [x.strip() for x in re.split("[;；]", conditions)]:
                    if illegal_condition(condition):
                        warning += (
                            gui_text("msg_warn_user_node_bad_condition")
                            % (short_id, conditions)
                            + "\n"
                        )

            # actions（GraphScene 形式の 'action' フィールド）
            actions = str(node.get("action", "")).strip()
            if actions != "":
                warning += (
                    gui_text("msg_warn_user_node_action_note") % (short_id, actions)
                    + "\n"
                )

            # 接続先が存在するか（出力側：edges[].from に含まれるか）
            if node_id not in connect_sources:
                warning += (
                    gui_text("msg_warn_user_node_no_transition_dest") % short_id + "\n"
                )

        # システムノード判定（GraphScene の 'type' を参照）
        is_system = bool(ntype and str(ntype).lower().startswith("system"))

        if is_system:
            # system の種別（pyeditor: 'node_kind' を採用）
            system_node_type: str = str(node.get("node_kind", "")).strip()

            if system_node_type == "":
                warning += gui_text("msg_warn_sys_node_no_type") % short_id + "\n"
            else:
                if system_node_type == "initial":
                    initial_node_exists = True
                elif system_node_type == "error":
                    error_node_exists = True

            # 発話（pyeditor: 'utterance'）
            utterance: str = str(node.get("utterance", "")).strip()
            if utterance == "":
                warning += gui_text("msg_warn_sys_node_utter_empty") % short_id + "\n"

    if not initial_node_exists:
        warning += gui_text("msg_warn_initial_node_exists") + "\n"
    if not error_node_exists:
        warning += gui_text("msg_warn_error_node_exists") + "\n"

    return warning


def check_kind_duplicates(node_data: dict, kinds: list) -> str:
    """
    指定したシステムノード種別（例: ["prep","initial","error"]）について重複を検査し、
    重複があれば警告メッセージを返す。重複がなければ空文字を返す。

    対応する JSON 構造:
    - `node_kind` フィールドを持つ（pyeditor の export 形式）
    - または `controls.type.value` を持つ（no_code の形式）
    """
    counts = {k: 0 for k in kinds}

    for node in node_data.get("nodes", []):
        kind = str(node.get("node_kind", "")).strip()

        if kind in counts:
            counts[kind] += 1

    violations = [f"{k}: {v} 個" for k, v in counts.items() if v > 1]
    if violations:
        return gui_text("msg_warn_kind_duplicates") % ("\n".join(violations))
    return ""
