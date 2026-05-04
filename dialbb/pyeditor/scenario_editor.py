import argparse
import sys
import os
import math
import json
import uuid
from collections import deque
from PySide6 import QtCore, QtGui, QtWidgets

from constants import (
    CONNECTOR_OUTSIDE,
    CONNECTOR_R,
    DATA_PATH,
    DEFAULT_NODE_KINDS,
    IMPORT_LAYOUT_BASE_X,
    INITIAL_VIEW_SCALE,
    NODE_CORNER_R,
    NODE_H_SYSTEM,
    NODE_H_USER,
    NODE_HEADER_H,
    NODE_TYPE_SYSTEM,
    NODE_TYPE_USER,
    NODE_W,
    PAD,
    SHADOW_DX,
    SHADOW_DY,
    SHORT_ID_DIGITS,
    SYS_UTTERANCE_H,
    USR_CONDITION_H,
)
from node_checks import node_check_and_warn, check_kind_duplicates
from dialbb.no_code.gui_utils import read_gui_text_data, gui_text

# ==================================
# ノードIDの表示用（6桁数字・人が読む用の短いID）
# ==================================
_SHORT_ID_STATE = {"next": 1}


def _format_short_id(value: int) -> str:
    """整数IDを固定桁（SHORT_ID_DIGITS）の文字列に整形する。"""
    return f"{value:0{SHORT_ID_DIGITS}d}"


def generate_short_id() -> str:
    """表示用の連番 short_id を1件払い出して返す。"""
    short_id = _format_short_id(_SHORT_ID_STATE["next"])
    _SHORT_ID_STATE["next"] += 1
    return short_id


def sync_short_id_counter(short_ids: list[str]) -> None:
    """既存 short_id 一覧から次に採番する番号を同期する。"""
    max_id = 0
    for short_id in short_ids:
        if short_id and short_id.isdigit():
            max_id = max(max_id, int(short_id))

    _SHORT_ID_STATE["next"] = max(max_id + 1, 1)


# ==================================
# ノード編集ダイアログ（モーダル）
# ==================================
class NodeEditDialog(QtWidgets.QDialog):
    """System/User ノードの編集を行うモーダルダイアログ。"""

    def __init__(self, node: "NodeItem", state_list=None, parent=None):
        """ノード編集ダイアログを初期化する。"""
        super().__init__(parent)
        self.node = node
        self.state_list = state_list or []
        self.setModal(True)
        self.setWindowTitle(gui_text("scn_node_edit_title"))

        # UI構築 → ノード値の読み込み
        self._build_ui()
        self._load_from_node()

    def _build_ui(self):
        """編集UIを組み立てる（System/Userでフォームが異なる）"""
        self.resize(640, 520)

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        # ---- form（入力エリア） ----
        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        # System用フォーム
        if self.node.node_type == NODE_TYPE_SYSTEM:
            # ノードタイプ: Combo
            self.node_kind = QtWidgets.QComboBox()
            # デフォルトのノード種別とSceneから渡されたstate候補をマージする（重複除去）
            states_set = list(dict.fromkeys(DEFAULT_NODE_KINDS
                                             + (self.state_list or [])))
            self.node_kind.addItems(states_set)
            self.node_kind.setMinimumWidth(240)

            # 発話: Text
            self.utterance = QtWidgets.QTextEdit()
            self.utterance.setMinimumHeight(120)

            form.addRow(gui_text("scn_form_node_type"), self.node_kind)
            form.addRow(gui_text("scn_form_utterance"), self.utterance)

        # User用フォーム
        else:
            # 優先度: SpinBox
            self.priority = QtWidgets.QSpinBox()
            self.priority.setRange(0, 10**9)
            self.priority.setMinimumWidth(120)

            # ユーザ発話タイプ: Text
            #self.utterance_type = QtWidgets.QTextEdit()
            #self.utterance_type.setMinimumHeight(60)

            # 遷移条件: Text
            self.condition = QtWidgets.QTextEdit()
            self.condition.setMinimumHeight(140)

            # 遷移時アクション: Text
            self.action = QtWidgets.QTextEdit()
            self.action.setMinimumHeight(80)

            form.addRow(gui_text("scn_form_priority"), self.priority)
            #form.addRow(gui_text("scn_form_user_utterance_type"), self.utterance_type)
            form.addRow(gui_text("scn_form_transition_condition"), self.condition)
            form.addRow(gui_text("scn_form_transition_action_advanced"), self.action)

        root.addLayout(form)
        root.addStretch(1)

        # ---- buttons（保存/キャンセル） ----
        btns = QtWidgets.QDialogButtonBox()
        btn_cancel = btns.addButton(gui_text("btn_cancel"), QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        btn_ok = btns.addButton(gui_text("scn_btn_save"), QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        btn_ok.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        btn_cancel.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)

        # ---- Tab操作：入力→次の入力へ ----
        # QTextEditのTabキーを「Tab文字入力」ではなく「次の入力へ」にする
        if self.node.node_type == NODE_TYPE_SYSTEM:
            self.utterance.setTabChangesFocus(True)
        else:
            #self.utterance_type.setTabChangesFocus(True)
            self.condition.setTabChangesFocus(True)
            self.action.setTabChangesFocus(True)

        # ---- Tab順序：このダイアログ内だけで完結させる ----
        widgets = []
        if self.node.node_type == NODE_TYPE_SYSTEM:
            widgets = [self.node_kind, self.utterance]
        else:
            # widgets = [self.priority, self.utterance_type, self.condition, self.action]
            widgets = [self.priority, self.condition, self.action]

        for w in widgets:
            w.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        btn_cancel.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        btn_ok.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Tab順（同一Dialog内のみ）
        if self.node.node_type == NODE_TYPE_SYSTEM:
            QtWidgets.QWidget.setTabOrder(self.node_kind, self.utterance)
            QtWidgets.QWidget.setTabOrder(self.utterance, btn_cancel)
            QtWidgets.QWidget.setTabOrder(btn_cancel, btn_ok)
            self.node_kind.setFocus()  # 初期フォーカス
        else:
            #QtWidgets.QWidget.setTabOrder(self.priority, self.utterance_type)
            #QtWidgets.QWidget.setTabOrder(self.utterance_type, self.condition)
            QtWidgets.QWidget.setTabOrder(self.priority, self.condition)
            QtWidgets.QWidget.setTabOrder(self.condition, self.action)
            QtWidgets.QWidget.setTabOrder(self.action, btn_cancel)
            QtWidgets.QWidget.setTabOrder(btn_cancel, btn_ok)
            self.priority.setFocus()   # 初期フォーカス

        root.addWidget(btns)

    def _load_from_node(self):
        """ノード→ダイアログへ値を反映"""
        if self.node.node_type == NODE_TYPE_SYSTEM:
            kind = self.node.get_field("node_kind") or ""
            idx = self.node_kind.findText(kind)
            if idx >= 0:
                self.node_kind.setCurrentIndex(idx)
            self.utterance.setPlainText(self.node.get_field("utterance"))
        else:
            pr = self.node.get_field("priority")
            try:
                self.priority.setValue(int(pr) if pr != "" else 0)
            except ValueError:
                self.priority.setValue(0)

            # self.utterance_type.setPlainText(self.node.get_field("utterance_type"))
            self.condition.setPlainText(self.node.get_field("condition"))
            self.action.setPlainText(self.node.get_field("action"))

    def apply_to_node(self):
        """ダイアログ→ノードへ値を反映（OK時に呼ぶ）"""
        if self.node.node_type == NODE_TYPE_SYSTEM:
            self.node.set_field("node_kind", self.node_kind.currentText())
            self.node.set_field("utterance", self.utterance.toPlainText())
        else:
            self.node.set_field("priority", str(self.priority.value()))
            # self.node.set_field("utterance_type", self.utterance_type.toPlainText())
            self.node.set_field("condition", self.condition.toPlainText())
            self.node.set_field("action", self.action.toPlainText())


# =========================
# コネクタ（ノードの接続点）
# =========================
class ConnectorItem(QtWidgets.QGraphicsEllipseItem):
    """ノードの入出力接続点を表す GraphicsItem。"""

    def __init__(self, parent_node, name, x, y):
        """ノード上の接続点（コネクタ）を作成する。"""
        super().__init__(-CONNECTOR_R, -CONNECTOR_R, CONNECTOR_R * 2, CONNECTOR_R * 2)
        self.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
        self.setPen(QtGui.QPen(QtGui.QColor("#333333")))
        self.setZValue(2)
        self.name = name
        self.node = parent_node
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def center_scene_pos(self):
        """エッジ描画用：コネクタ中心のScene座標を返す"""
        return self.mapToScene(self.boundingRect().center())


# =========================
# エッジ（ベジェ曲線）
# =========================
class EdgeItem(QtWidgets.QGraphicsPathItem):
    """Bezier edge with thick hit area."""
    HIT_STROKE_WIDTH = 12.0  # 見た目より太い当たり判定

    def __init__(self, from_connector, to_connector):
        """2つのコネクタ間を結ぶ有向エッジを初期化する。"""
        super().__init__()
        self.from_conn = from_connector
        self.to_conn = to_connector

        pen = QtGui.QPen(QtGui.QColor("#000000"))
        pen.setWidth(2)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setZValue(0)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        # 矢印の大きさ
        self.arrow_size = 12
        self._p1 = None
        self._p2 = None
        self._c1 = None
        self._c2 = None

        self.update_positions()

    def update_positions(self):
        """始点/終点コネクタ位置からベジェ曲線を再計算"""
        p1 = self.from_conn.center_scene_pos()
        p2 = self.to_conn.center_scene_pos()

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        c = max(60.0, min(220.0, abs(dx) * 0.5 + abs(dy) * 0.15))

        c1 = QtCore.QPointF(p1.x() + c, p1.y())
        c2 = QtCore.QPointF(p2.x() - c, p2.y())

        path = QtGui.QPainterPath(p1)
        path.cubicTo(c1, c2, p2)
        self.setPath(path)

        # store points for arrow drawing
        self._p1 = p1
        self._p2 = p2
        self._c1 = c1
        self._c2 = c2

    def paint(self, painter: QtGui.QPainter, _option, _widget=None):
        """Draw the edge path and an arrow on the 'to' end to indicate direction."""
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        pen = self.pen()
        painter.setPen(pen)
        # draw main path
        painter.drawPath(self.path())

        # draw arrow at end (use last control point to estimate tangent)
        if not self._p2 or not self._c2:
            return

        dx = self._p2.x() - self._c2.x()
        dy = self._p2.y() - self._c2.y()
        length = math.hypot(dx, dy)
        if length < 1e-6:
            dx = self._p2.x() - (self._p1.x() if self._p1 else 0)
            dy = self._p2.y() - (self._p1.y() if self._p1 else 0)
            length = math.hypot(dx, dy)
            if length < 1e-6:
                return

        ux = dx / length
        uy = dy / length

        size = self.arrow_size
        # base point a bit back from p2
        bx = self._p2.x() - ux * size
        by = self._p2.y() - uy * size

        # perpendicular for arrow width
        px = -uy * (size * 0.6)
        py = ux * (size * 0.6)

        left = QtCore.QPointF(bx + px, by + py)
        right = QtCore.QPointF(bx - px, by - py)

        poly = QtGui.QPolygonF([self._p2, left, right])
        painter.setBrush(QtGui.QBrush(pen.color()))
        painter.drawPolygon(poly)

    def shape(self) -> QtGui.QPainterPath:
        """選択しやすいように当たり判定だけ太くする"""
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(self.HIT_STROKE_WIDTH)
        stroker.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(self.path())

    def itemChange(self, change, value):
        """選択時は色/太さを変えて視認性UP"""
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            selected = bool(value)
            pen = self.pen()
            if selected:
                pen.setColor(QtGui.QColor("blue"))
                pen.setWidth(3)
            else:
                pen.setColor(QtGui.QColor("#000000"))
                pen.setWidth(2)
            self.setPen(pen)
        return super().itemChange(change, value)


# =========================
# ノード（System/User）
# =========================
class NodeItem(QtWidgets.QGraphicsItem):
    """System/User ノード本体の描画・値保持・接続管理を担う。"""

    def __init__(self, x, y, text="State", node_id=None, node_type=NODE_TYPE_USER):
        """System/User ノード本体を作成して初期表示を構築する。"""
        super().__init__()

        # ノード基本情報（固定サイズ方針）
        self.node_w = NODE_W
        self.node_h = NODE_H_SYSTEM if node_type == NODE_TYPE_SYSTEM else NODE_H_USER
        self.node_id = node_id or str(uuid.uuid4())   # 内部用（絶対一意）
        self.short_id = generate_short_id()           # 表示用（人間向け）
        self.node_type = node_type

        # 選択/移動ができるGraphicsItem
        self.setZValue(1)
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # 見た目（System/Userで配色を切り替え）
        if self.node_type == NODE_TYPE_SYSTEM:
            self.body_color = QtGui.QColor("#f7c9a6")
            self.header_color = QtGui.QColor("#f0ad82")
            self.border_color = QtGui.QColor("#b07a55")
        else:
            self.body_color = QtGui.QColor("#8fc3ff")
            self.header_color = QtGui.QColor("#6aaaf2")
            self.border_color = QtGui.QColor("#4f78a8")

        # タイトル（ヘッダー内に描画）
        self.title_item = QtWidgets.QGraphicsSimpleTextItem(text, self)
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.title_item.setFont(font)
        self.title_item.setBrush(QtGui.QBrush(QtGui.QColor("#0b1b2b")))

        # 非表示のフィールド（フォームには表示しないがJSONで引き継ぎたいデータ）
        # 初期値をここで設定しておく（フォームがまだ未生成のケースに備える）
        if self.node_type == NODE_TYPE_SYSTEM:
            self.hidden_fields: dict[str, str] = {
                "node_kind": "initial",
                "utterance": "",
                "utterance_example": "",
            }
        else:
            self.hidden_fields: dict[str, str] = {
                "utterance_example": ""
            }

        # コネクタ・エッジ管理
        self.connectors = {}
        self._create_connectors()
        self.edges = []

        # ノード内フォーム（読み取り表示用：編集はダブルクリックのモーダル）
        self.form_proxy = None
        self._build_form()

        # 初期レイアウト
        self._layout_texts()

    # ---- geometry（当たり判定 / 描画領域） ----
    def boundingRect(self) -> QtCore.QRectF:
        """影や選択枠を含めた描画領域（Sceneの更新・当たり判定に必須）"""
        base = QtCore.QRectF(-self.node_w / 2, -self.node_h / 2, self.node_w, self.node_h)
        return base.adjusted(-PAD, -PAD, SHADOW_DX + PAD, SHADOW_DY + PAD)

    def shape(self) -> QtGui.QPainterPath:
        """選択の当たり判定（角丸の本体形状に合わせる）"""
        base = QtCore.QRectF(-self.node_w / 2, -self.node_h / 2, self.node_w, self.node_h)
        path = QtGui.QPainterPath()
        path.addRoundedRect(base, NODE_CORNER_R, NODE_CORNER_R)
        return path

    # ---- paint（ノード見た目の描画） ----
    def paint(self, painter: QtGui.QPainter, _option, _widget=None):
        """ノードのカード風描画（影/本体/ヘッダー/IDバッジ/選択枠）"""
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        r = self.boundingRect()

        # 影
        shadow = QtCore.QRectF(r)
        shadow.translate(2, 3)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 40))
        painter.drawRoundedRect(shadow, NODE_CORNER_R, NODE_CORNER_R)

        # 本体
        painter.setBrush(self.body_color)
        painter.setPen(QtGui.QPen(self.border_color, 2))
        painter.drawRoundedRect(r, NODE_CORNER_R, NODE_CORNER_R)

        # ヘッダー
        header = QtCore.QRectF(r.left(), r.top(), r.width(), NODE_HEADER_H)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(self.header_color)
        painter.drawRoundedRect(header, NODE_CORNER_R, NODE_CORNER_R)

        # ヘッダー下ライン
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 40), 1))
        painter.drawLine(header.bottomLeft(), header.bottomRight())

        # IDバッジ（右上）
        badge_text = self.short_id
        badge_font = QtGui.QFont()
        badge_font.setPointSize(8)
        painter.setFont(badge_font)

        metrics = QtGui.QFontMetrics(badge_font)
        tw = metrics.horizontalAdvance(badge_text)
        th = metrics.height()

        pad_x, pad_y = 8, 4
        badge_w = tw + pad_x * 2
        badge_h = th + pad_y * 2

        badge_rect = QtCore.QRectF(
            r.right() - badge_w - 10,
            r.top() + (NODE_HEADER_H - badge_h) / 2,
            badge_w,
            badge_h,
        )

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 200), 1))
        painter.setBrush(QtGui.QColor(255, 255, 255, 230))
        painter.drawRoundedRect(badge_rect, 8, 8)

        painter.setPen(QtGui.QPen(QtGui.QColor("#1b2b3a")))
        painter.drawText(badge_rect, QtCore.Qt.AlignmentFlag.AlignCenter, badge_text)

        # 選択枠
        if self.isSelected():
            sel_pen = QtGui.QPen(QtGui.QColor("#2d6cff"), 3)
            sel_pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
            painter.setPen(sel_pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), NODE_CORNER_R, NODE_CORNER_R)

    # ---- ノード内のフォーム表示（ProxyWidget） ----
    def _build_form(self):
        """ノード内に「読み取り専用フォーム」を固定配置で載せる（編集はダイアログ）"""
        if hasattr(self, "form_proxy") and self.form_proxy is not None:
            scene = self.scene()
            if scene is not None:
                scene.removeItem(self.form_proxy)
            self.form_proxy = None

        self.form_widget = QtWidgets.QWidget()
        self.form_widget.setObjectName("nodeForm")

        # レイアウト（フォーム外枠の余白）
        v = QtWidgets.QVBoxLayout(self.form_widget)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)

        # ノードタイプ別：フォーム項目を固定で構築
        if self.node_type == NODE_TYPE_SYSTEM:
            self._add_labeled_line(v, gui_text("scn_form_node_type_plain"), "initial", key="node_kind")
            self._add_labeled_text(v, gui_text("scn_form_utterance_plain"), "", key="utterance", min_h=SYS_UTTERANCE_H)
        else:
            self._add_labeled_line(v, gui_text("scn_form_priority_plain"), "", key="priority")
            # self._add_labeled_line(v, gui_text("scn_form_user_utterance_type_plain"), "", key="utterance_type")
            self._add_labeled_text(v, gui_text("scn_form_transition_condition_plain"), "", key="condition", min_h=USR_CONDITION_H)
            self._add_labeled_line(v, gui_text("scn_form_transition_action_plain"), "", key="action")

        v.addStretch(1)

        # Proxyとしてノードへ載せる（ヘッダー下の本文領域に収める）
        self.form_proxy = QtWidgets.QGraphicsProxyWidget(self)
        self.form_proxy.setWidget(self.form_widget)

        r = self.boundingRect()
        content_x = r.left()
        content_y = r.top() + NODE_HEADER_H
        content_w = r.width()
        content_h = r.height() - NODE_HEADER_H

        self.form_proxy.setPos(content_x, content_y)
        self.form_widget.setFixedSize(int(content_w), int(content_h))

        # フォームの見た目（入力欄は白カード風）
        self.form_widget.setStyleSheet("""
            QWidget#nodeForm { background: transparent; }
            QLabel { color: #0b1b2b; font-size: 10pt; }
            QLineEdit, QTextEdit {
                background: rgba(255,255,255,230);
                border: 1px solid rgba(0,0,0,50);
                border-radius: 10px;
                padding: 1px 3px;
                font-size: 10pt;
            }
            QTextEdit { padding: 1px 3px; }
            QTextEdit QAbstractScrollArea::viewport {
                margin: 0px;
            }
        """)

        # z順（フォームは下、タイトルは上）
        self.form_proxy.setZValue(0)
        self.title_item.setZValue(2)

        # 表示用なので読み取り専用にする
        for w in self.form_widget.findChildren(QtWidgets.QLineEdit):
            w.setReadOnly(True)
        for w in self.form_widget.findChildren(QtWidgets.QTextEdit):
            w.setReadOnly(True)

        self.update()

    def _add_labeled_line(self, layout: QtWidgets.QVBoxLayout, label: str, default: str, key: str):
        """フォーム：ラベル + 1行入力"""
        lab = QtWidgets.QLabel(label)
        edit = QtWidgets.QLineEdit()
        edit.setText(default)
        edit.setObjectName(key)
        layout.addWidget(lab)
        layout.addWidget(edit)

    def _add_labeled_text(self, layout: QtWidgets.QVBoxLayout, label: str, default: str, key: str, min_h: int = 80):
        """フォーム：ラベル + 複数行入力（表示用）"""
        lab = QtWidgets.QLabel(label)
        edit = QtWidgets.QTextEdit()
        edit.setPlainText(default)
        edit.setMinimumHeight(min_h)
        edit.setObjectName(key)
        edit.document().setDocumentMargin(0)  # 内側余白の微調整
        layout.addWidget(lab)
        layout.addWidget(edit)

    # ---- connectors（左右に固定配置） ----
    def _create_connectors(self):
        """接続点をノード左右に配置（タイトル直下付近）"""
        edge_offset = CONNECTOR_OUTSIDE
        xL = -self.node_w / 2 + edge_offset
        xR =  self.node_w / 2 - edge_offset

        title_h = self.title_item.boundingRect().height()
        top = -self.node_h / 2
        y = top + title_h - 4

        self.connectors["left"] = ConnectorItem(self, "left", xL, y)
        self.connectors["right"] = ConnectorItem(self, "right", xR, y)

        for c in self.connectors.values():
            c.setParentItem(self)

    # ---- header text layout ----
    def _layout_texts(self):
        """タイトル文字をヘッダー内に配置"""
        r = self.boundingRect()
        self.title_item.setPos(r.left() + 12, r.top() + 7)

    # ---- edge list maintenance ----
    def add_edge(self, edge: EdgeItem):
        """ノードが持つ接続エッジ一覧へ追加"""
        if edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge: EdgeItem):
        """ノードが持つ接続エッジ一覧から除去"""
        try:
            self.edges.remove(edge)
        except ValueError:
            pass

    def itemChange(self, change, value):
        """ノード移動時に接続エッジを追従更新"""
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for e in list(self.edges):
                e.update_positions()
        return super().itemChange(change, value)

    # ---- form field access (JSON/ダイアログ連携用) ----
    def get_field(self, key: str) -> str:
        """フォーム値取得（QLineEdit/QTextEditをキーで取得）"""
        w = self.form_widget.findChild(QtWidgets.QWidget, key)
        if isinstance(w, QtWidgets.QLineEdit):
            return w.text()
        if isinstance(w, QtWidgets.QTextEdit):
            return w.toPlainText()
        # フォームに無い＝hidden
        return self.hidden_fields.get(key, "")

    def set_field(self, key: str, value: str):
        """フォーム値設定（表示更新・JSON読み込み用）"""
        w = self.form_widget.findChild(QtWidgets.QWidget, key) if hasattr(self, "form_widget") else None
        if isinstance(w, QtWidgets.QLineEdit):
            w.setText(value or "")
            return
        elif isinstance(w, QtWidgets.QTextEdit):
            w.setPlainText(value or "")
            return
        # フォームに無い＝hidden
        if not hasattr(self, "hidden_fields"):
            self.hidden_fields = {}
        # 既に hidden_fields がある場合でも値を上書きする
        self.hidden_fields[key] = value or ""


# ==================================
# Undo/Redo：Sceneスナップショットコマンド
# ==================================
class GraphHistoryCommand(QtGui.QUndoCommand):
    """Scene全体の before/after を保存して Undo/Redo する（スナップショット方式）"""

    def __init__(self, scene, before_state: dict, after_state: dict, description: str):
        """Undo/Redo 用の前後スナップショットを保持する。"""
        super().__init__(description)
        self.scene = scene
        self.before_state = before_state
        self.after_state = after_state
        self._first = True  # push直後のredoは「現状維持」になるのでスキップ

    def undo(self):
        """before_state を Scene に復元する。"""
        self.scene._load_state_from_dict(self.before_state)

    def redo(self):
        """after_state を Scene に復元する。"""
        if self._first:
            self._first = False
            return
        self.scene._load_state_from_dict(self.after_state)


# =========================
# 自動整列：間隔設定
# =========================
LAYOUT_DX = NODE_W * 2        # レベル間の横距離
LAYOUT_DY = NODE_H_USER + 50  # 縦並びの間隔（重なり防止）


# ==================================
# Scene：編集操作の中心（追加/接続/Undo/整列）
# ==================================
class GraphScene(QtWidgets.QGraphicsScene):
    """ノード編集操作全体を管理する Scene。"""

    SCENE_MARGIN_X = 200
    SCENE_MARGIN_Y = 140
    MIN_SCENE_W = 1200
    MIN_SCENE_H = 800

    def __init__(self, undo_stack: QtGui.QUndoStack | None = None, parent=None):
        """ノード編集用の Scene を初期化する。"""
        super().__init__(parent)
        self.nodes: list[NodeItem] = []
        self.edges: list[EdgeItem] = []
        self.temp_line: QtWidgets.QGraphicsLineItem | None = None
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))

        # UndoStack（無い場合は履歴なしモード）
        self.undo_stack = undo_stack

        # ノード移動のUndo用：ドラッグ開始/終了のスナップショット
        self._drag_before_state: dict | None = None
        self._drag_start_positions: dict[NodeItem, QtCore.QPointF] = {}
        self._dragging_nodes: bool = False
        self._drag_start: ConnectorItem | None = None

        # 初期状態でもパン可能な最小範囲を確保
        self.update_scene_rect_to_contents()

    def update_scene_rect_to_contents(self):
        """現在の内容に合わせてScene範囲を更新する（左右余白を最小化）。"""
        rect = self.itemsBoundingRect()

        if rect.isNull():
            self.setSceneRect(
                -self.MIN_SCENE_W / 2,
                -self.MIN_SCENE_H / 2,
                self.MIN_SCENE_W,
                self.MIN_SCENE_H,
            )
            return

        rect = rect.adjusted(
            -self.SCENE_MARGIN_X,
            -self.SCENE_MARGIN_Y,
            self.SCENE_MARGIN_X,
            self.SCENE_MARGIN_Y,
        )

        if rect.width() < self.MIN_SCENE_W:
            pad = (self.MIN_SCENE_W - rect.width()) / 2
            rect = rect.adjusted(-pad, 0, pad, 0)
        if rect.height() < self.MIN_SCENE_H:
            pad = (self.MIN_SCENE_H - rect.height()) / 2
            rect = rect.adjusted(0, -pad, 0, pad)

        self.setSceneRect(rect)

    def _find_ancestor_item(self, item):
        """Proxy内の子Widget等からでも Node/Connector/Edge を拾うための親たどり"""
        while item is not None and not isinstance(item, (NodeItem, ConnectorItem, EdgeItem)):
            item = item.parentItem()
        return item

    def get_all_system_states(self) -> list[str]:
        """
        Scene内のすべてのSystemノードの node_kind を収集し、
        重複無しリストを返す
        """
        states = set()

        for n in self.nodes:
            if n.node_type == NODE_TYPE_SYSTEM:
                kind = n.get_field("node_kind")
                if kind:
                    states.add(kind)

        return sorted(states)

    # ---------- remove helpers（一貫した削除処理） ----------
    def remove_edge(self, edge: EdgeItem):
        """Sceneからエッジを削除し、両端ノードの参照も外す"""
        if edge in self.edges:
            self.edges.remove(edge)
        try:
            edge.from_conn.node.remove_edge(edge)
        except Exception:
            pass
        try:
            edge.to_conn.node.remove_edge(edge)
        except Exception:
            pass
        self.removeItem(edge)

    def remove_node(self, node: NodeItem):
        """ノード削除：接続しているエッジを先に全削除してからノードを消す"""
        for e in list(node.edges):
            self.remove_edge(e)
        if node in self.nodes:
            self.nodes.remove(node)
        self.removeItem(node)

    # ---------- double click：ノード編集（モーダル） ----------
    def mouseDoubleClickEvent(self, event):
        """ダブルクリック：ノードなら編集ダイアログを開く（Undo対応）"""
        pos = event.scenePos()
        raw = self.itemAt(pos, QtGui.QTransform())
        item = self._find_ancestor_item(raw)
        state_list = self.get_all_system_states()

        if isinstance(item, NodeItem):
            if self.undo_stack is not None:
                before = self._state_to_dict()
                dlg = NodeEditDialog(item, state_list=state_list)
                if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    dlg.apply_to_node()
                    after = self._state_to_dict()
                    self.undo_stack.push(GraphHistoryCommand(self, before, after, "ノード編集"))
            else:
                dlg = NodeEditDialog(item, state_list=state_list)
                if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    dlg.apply_to_node()

            event.accept()
            return

        event.accept()

    # ---------- mouse：接続ドラッグ / ノード移動のUndo ----------
    def mousePressEvent(self, event):
        """押下：コネクタなら接続ドラッグ開始、ノードなら移動Undoの準備"""
        raw = self.itemAt(event.scenePos(), QtGui.QTransform())
        item = self._find_ancestor_item(raw)

        # エッジ作成ドラッグ開始（コネクタ→線を引く）
        if isinstance(item, ConnectorItem):
            start = item
            self.temp_line = QtWidgets.QGraphicsLineItem(
                QtCore.QLineF(start.center_scene_pos(), start.center_scene_pos())
            )
            pen = QtGui.QPen(QtGui.QColor("gray"))
            pen.setStyle(QtCore.Qt.PenStyle.DashLine)
            pen.setWidth(2)
            self.temp_line.setPen(pen)
            self.temp_line.setZValue(-1)
            self.addItem(self.temp_line)
            self._drag_start = start
            return

        # ノード移動のUndo準備（ドラッグ開始前の状態を保存）
        if isinstance(item, NodeItem) and self.undo_stack is not None:
            self._drag_before_state = self._state_to_dict()
            self._drag_start_positions = {n: QtCore.QPointF(n.pos()) for n in self.nodes}
            self._dragging_nodes = True

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """移動：エッジ作成中なら仮線を更新、通常時はデフォルト処理"""
        if self.temp_line is not None and self._drag_start is not None:
            p1 = self._drag_start.center_scene_pos()
            p2 = event.scenePos()
            self.temp_line.setLine(p1.x(), p1.y(), p2.x(), p2.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """解放：エッジ確定 or ノード移動のUndo確定"""
        # エッジ作成ドラッグ終了
        if self.temp_line is not None and self._drag_start is not None:
            items = self.items(event.scenePos())
            target = None
            for it in items:
                ancestor = self._find_ancestor_item(it)
                if isinstance(ancestor, ConnectorItem) and ancestor is not self._drag_start:
                    target = ancestor
                    break

            if target is not None:
                self.create_edge(self._drag_start, target)

            self.removeItem(self.temp_line)
            self.temp_line = None
            self._drag_start = None
            return

        # 通常のクリック/ドラッグ終了
        super().mouseReleaseEvent(event)

        # ノード移動があった場合だけ「ノード移動」履歴を積む
        if self._dragging_nodes and self.undo_stack is not None and self._drag_before_state is not None:
            moved = False
            for n in self.nodes:
                old_pos = self._drag_start_positions.get(n)
                if old_pos is not None and (n.pos() != old_pos):
                    moved = True
                    break

            if moved:
                before = self._drag_before_state
                after = self._state_to_dict()
                self.undo_stack.push(GraphHistoryCommand(self, before, after, "ノード移動"))
                self.update_scene_rect_to_contents()

        # 後片付け
        self._dragging_nodes = False
        self._drag_before_state = None
        self._drag_start_positions = {}

    # ---------- edge create：履歴あり/なしを分離 ----------
    def _create_edge_raw(self, from_conn: ConnectorItem, to_conn: ConnectorItem):
        """履歴を積まないエッジ生成（Undo/Redo・インポート時に使用）"""
        from_node = from_conn.node
        to_node = to_conn.node

        if from_node is to_node:
            return None
        if not self.can_connect(from_node, to_node):
            return None
        for e in self.edges:
            if e.from_conn is from_conn and e.to_conn is to_conn:
                return None

        edge = EdgeItem(from_conn, to_conn)
        self.addItem(edge)
        self.edges.append(edge)
        from_node.add_edge(edge)
        to_node.add_edge(edge)
        return edge

    def create_edge(self, from_conn: ConnectorItem, to_conn: ConnectorItem):
        """履歴つきのエッジ生成（通常操作はこちら）"""
        def do():
            """履歴エントリ内でエッジ生成を実行する。"""
            self._create_edge_raw(from_conn, to_conn)
        self._push_history("エッジ追加", do)

    def delete_selected(self):
        """選択中のノード/エッジを削除（履歴つき）"""
        def do():
            """履歴エントリ内で選択アイテムを削除する。"""
            for item in list(self.selectedItems()):
                if isinstance(item, EdgeItem):
                    self.remove_edge(item)
                elif isinstance(item, NodeItem):
                    self.remove_node(item)
        self._push_history("選択削除", do)

    def can_connect(self, from_node: NodeItem, to_node: NodeItem) -> bool:
        """接続ルール：System↔Userのみ許可（同種同士は不可）"""
        return from_node.node_type != to_node.node_type

    # ---------- context menu：追加/編集/削除 ----------
    def contextMenuEvent(self, event: QtWidgets.QGraphicsSceneContextMenuEvent):
        """右クリックメニュー：空白=追加、ノード=編集/整列/削除、エッジ=削除"""
        pos = event.scenePos()
        raw = self.itemAt(pos, QtGui.QTransform())
        item = self._find_ancestor_item(raw)

        if isinstance(item, (NodeItem, EdgeItem)):
            self.clearSelection()
            item.setSelected(True)

        menu = QtWidgets.QMenu()

        # 空白：System/User追加
        if item is None:
            act_sys = menu.addAction(gui_text("scn_menu_add_system"))
            act_user = menu.addAction(gui_text("scn_menu_add_user"))
            menu.addSeparator()
            menu.addAction(gui_text("btn_cancel"))

            chosen = menu.exec(event.screenPos())
            if chosen == act_sys:
                def do():
                    """Systemノード追加を履歴付きで実行する。"""
                    node = NodeItem(pos.x(), pos.y(), text=gui_text("scn_node_label_system"), node_type=NODE_TYPE_SYSTEM)
                    self.addItem(node)
                    self.nodes.append(node)
                self._push_history("Systemノード追加", do)

            elif chosen == act_user:
                def do():
                    """Userノード追加を履歴付きで実行する。"""
                    node = NodeItem(pos.x(), pos.y(), text=gui_text("scn_node_label_user"), node_type=NODE_TYPE_USER)
                    self.addItem(node)
                    self.nodes.append(node)
                self._push_history("Userノード追加", do)

            event.accept()
            return

        # ノード：（Systemのみ）配下User整列 / 削除
        if isinstance(item, NodeItem):
            act_align = None
            if item.node_type == NODE_TYPE_SYSTEM:
                act_align = menu.addAction(gui_text("scn_menu_align_connected_users"))

            act_del = menu.addAction(gui_text("scn_menu_delete"))
            menu.addSeparator()
            menu.addAction(gui_text("btn_cancel"))

            chosen = menu.exec(event.screenPos())

            if act_align and chosen == act_align:
                self.align_users_under_system(item)

            elif chosen == act_del:
                self._push_history("ノード削除", lambda: self.remove_node(item))

            event.accept()
            return

        # エッジ：削除
        if isinstance(item, EdgeItem):
            act_del = menu.addAction(gui_text("scn_menu_delete"))
            menu.addSeparator()
            menu.addAction(gui_text("btn_cancel"))
            chosen = menu.exec(event.screenPos())
            if chosen == act_del:
                self._push_history("エッジ削除", lambda: self.remove_edge(item))
            event.accept()
            return

        super().contextMenuEvent(event)

    # ---------- state serialize：Undo/Redo・JSON共通 ----------
    def _state_to_dict(self) -> dict:
        """Scene全体（nodes/edges）を辞書化（Undo/Redo・export用）"""
        data = {"nodes": [], "edges": []}

        for n in self.nodes:
            node_data = {
                "id": n.node_id,
                "short_id": n.short_id,
                "x": n.x(),
                "y": n.y(),
                "text": n.title_item.text(),
                "type": n.node_type,
            }
            if n.node_type == NODE_TYPE_SYSTEM:
                node_data.update({
                    "node_kind": n.get_field("node_kind"),
                    "utterance": n.get_field("utterance"),
                })
            else:
                node_data.update({
                    "priority": n.get_field("priority"),
                    "utterance_example": n.get_field("utterance_example"),
                    # "utterance_type": n.get_field("utterance_type"),
                    "condition": n.get_field("condition"),
                    "action": n.get_field("action"),
                })
            data["nodes"].append(node_data)

        for e in self.edges:
            data["edges"].append(
                {
                    "from": e.from_conn.node.node_id,
                    "to": e.to_conn.node.node_id,
                    "from_conn": e.from_conn.name,
                    "to_conn": e.to_conn.name,
                }
            )
        return data

    def _load_state_from_dict(self, data: dict):
        """辞書からSceneを復元（Undo/Redo・import用、ここでは履歴を積まない）"""
        # 既存を全消し（参照も含めて）
        for e in list(self.edges):
            self.remove_edge(e)
        for n in list(self.nodes):
            self.remove_node(n)

        id_map: dict[str, NodeItem] = {}

        # nodes（NodeItem再生成）
        for n in data.get("nodes", []):
            node = NodeItem(
                n["x"], n["y"],
                n.get("text", "State"),
                node_id=n["id"],
                node_type=n.get("type", NODE_TYPE_USER),
            )
            node.short_id = n.get("short_id") or generate_short_id()

            self.addItem(node)
            self.nodes.append(node)
            id_map[node.node_id] = node

            # フィールド復元
            if node.node_type == NODE_TYPE_SYSTEM:
                node.set_field("node_kind", n.get("node_kind", ""))
                node.set_field("utterance", n.get("utterance", ""))
            else:
                node.set_field("priority", str(n.get("priority", "")))
                node.set_field("utterance_example", n.get("utterance_example", ""))
                # node.set_field("utterance_type", n.get("utterance_type", ""))
                node.set_field("condition", n.get("condition", ""))
                node.set_field("action", n.get("action", ""))

        # edges（raw版で復元：履歴に乗せない）
        for e in data.get("edges", []):
            from_node = id_map.get(e["from"])
            to_node = id_map.get(e["to"])
            if not from_node or not to_node:
                continue
            fc = from_node.connectors.get(e.get("from_conn", "right"))
            tc = to_node.connectors.get(e.get("to_conn", "left"))
            if fc and tc:
                self._create_edge_raw(fc, tc)

        sync_short_id_counter([n.short_id for n in self.nodes])
        self.update_scene_rect_to_contents()

    def _push_history(self, description: str, mutate_func):
        """操作前後のスナップショットを取り、UndoStackへ積む共通関数"""
        if self.undo_stack is None:
            mutate_func()
            self.update_scene_rect_to_contents()
            return

        before = self._state_to_dict()
        mutate_func()
        self.update_scene_rect_to_contents()
        after = self._state_to_dict()

        self.undo_stack.push(GraphHistoryCommand(self, before, after, description))

    # ---------- JSON export/import ----------
    def export_json(self, path):
        """現在の状態をJSONへ保存"""
        file_path = os.path.join(DATA_PATH, path)
        data = self._state_to_dict()

        # data(json)をnode_check_and_warnに渡して検査する
        warning = node_check_and_warn(data)
        if warning:
            msg = gui_text("scn_msg_export_warning_with_detail").format(detail=warning)
            QtWidgets.QMessageBox.warning(None, gui_text("scn_title_export_warning"), msg)
            return

        # --- validation: certain System node kinds must not appear more than once ---
        dup_warn = check_kind_duplicates(data, ["prep", "initial", "error"])
        if dup_warn:
            msg = gui_text("scn_msg_export_aborted_with_detail").format(detail=dup_warn)
            QtWidgets.QMessageBox.warning(None, gui_text("scn_title_export_warning"), msg)
            return

        # write JSON only if validation passed
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        QtWidgets.QMessageBox.information(
            None,
            gui_text("scn_title_export"),
            gui_text("scn_msg_export_done").format(path=os.path.abspath(file_path)),
        )

    def import_json(self, path):
        """JSONから復元（インポートも履歴に乗せる）"""
        file_path = os.path.join(DATA_PATH, path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            def do():
                """JSONの内容をSceneへ反映して表示位置を整列する。"""
                self._load_state_from_dict(data)
                self._auto_layout_impl(base_x=IMPORT_LAYOUT_BASE_X)

            self._push_history("JSONインポート", do)

            print(f"インポート {os.path.abspath(file_path)} を読み込みました")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, gui_text("scn_title_import_error"), str(exc))

    # ---------- PNG export ----------
    def save_png(self, path):
        """Sceneの見えている内容をPNGで保存"""
        rect = self.itemsBoundingRect()
        if rect.isNull():
            QtWidgets.QMessageBox.warning(None, gui_text("scn_title_save"), gui_text("scn_msg_nothing_to_save"))
            return

        margin = 20
        rect = rect.adjusted(-margin, -margin, margin, margin)

        scale = 2.0
        w = max(1, int(rect.width() * scale))
        h = max(1, int(rect.height() * scale))

        img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32)
        img.fill(QtGui.QColor("white"))

        painter = QtGui.QPainter(img)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        target = QtCore.QRectF(0, 0, w, h)
        self.render(painter, target, rect)
        painter.end()

        img.save(path)
        QtWidgets.QMessageBox.information(
            None,
            gui_text("scn_title_save"),
            gui_text("scn_msg_saved_to_path").format(path=os.path.abspath(path)),
        )

    # ---------- layout helpers：部分整列 / 全体整列 ----------
    def align_users_under_system(self, system_node: NodeItem):
        """Systemの接続先Userを priority（昇順）で縦整列（System右側へ配置）"""
        if system_node.node_type != NODE_TYPE_SYSTEM:
            return

        # 接続先Userを収集（System->User 方向のみ）
        users = []
        for e in system_node.edges:
            if e.from_conn.node is system_node:
                target = e.to_conn.node
                if target.node_type == NODE_TYPE_USER:
                    users.append(target)
        if not users:
            return

        # priorityソート（値が壊れていても落ちないように）
        def priority_of(node: NodeItem) -> int:
            """Userノードの priority を数値化して返す。"""
            try:
                return int(node.get_field("priority") or 0)
            except ValueError:
                return 0

        users.sort(key=priority_of, reverse=False)

        # System右側に等間隔で並べる（中心合わせ）
        base_x = system_node.x() + LAYOUT_DX
        center_y = system_node.y()

        n = len(users)
        start_y = center_y - (n - 1) * LAYOUT_DY / 2

        for i, user in enumerate(users):
            new_y = start_y + i * LAYOUT_DY
            user.setPos(base_x, new_y)

    def auto_layout(self):
        """全体整列（履歴つきの入口）"""
        self._push_history("自動整列", self._auto_layout_impl)

    def _auto_layout_impl(self, base_x: float = 0.0):
        """全体整列：BFSでレベル付け→左→右へ層配置、各層内は縦に重ならないよう整列"""
        if not self.nodes:
            return

        # 1) adjacency（無向）と incoming_count（root判定用の有向）を作成
        adj: dict[NodeItem, set[NodeItem]] = {}
        incoming_count: dict[NodeItem, int] = {n: 0 for n in self.nodes}

        for e in self.edges:
            a = e.from_conn.node
            b = e.to_conn.node

            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

            incoming_count[b] = incoming_count.get(b, 0) + 1
            incoming_count.setdefault(a, incoming_count.get(a, 0))

        # 2) ルート候補：incoming==0 のSystemを優先
        roots = [
            n for n in self.nodes
            if n.node_type == NODE_TYPE_SYSTEM and incoming_count.get(n, 0) == 0
        ]
        if not roots:
            roots = [n for n in self.nodes if incoming_count.get(n, 0) == 0]
        if not roots:
            roots = list(self.nodes)  # 完全ループなら全ノード起点

        # 3) BFSでレベル割当（0,1,2,...）
        level: dict[NodeItem, int] = {}
        q = deque()

        for r in roots:
            level[r] = 0
            q.append(r)

        while q:
            cur = q.popleft()
            cur_level = level[cur]
            for nb in adj.get(cur, []):
                if nb not in level:
                    level[nb] = cur_level + 1
                    q.append(nb)

        # 4) レベル未割当ノード（孤立など）を右側に追加で割当
        if len(level) < len(self.nodes):
            max_level = max(level.values()) if level else 0
            for n in self.nodes:
                if n not in level:
                    max_level += 1
                    level[n] = max_level

        # 5) レベルごとにグループ化
        levels: dict[int, list[NodeItem]] = {}
        for n, lv in level.items():
            levels.setdefault(lv, []).append(n)

        # 6) レベルを左→右に配置、レベル内は縦整列
        base_y = 0.0
        dy = LAYOUT_DY

        for lv in sorted(levels.keys()):
            nodes = levels[lv]
            x = base_x + lv * LAYOUT_DX

            # User層は priority、その他は現Y順（元の上下関係を維持）
            if all(n.node_type == NODE_TYPE_USER for n in nodes):
                def priority_of(node: NodeItem) -> int:
                    """User層整列用の priority 値を返す。"""
                    try:
                        return int(node.get_field("priority") or 0)
                    except ValueError:
                        return 0
                nodes_sorted = sorted(nodes, key=priority_of, reverse=False)
            else:
                nodes_sorted = sorted(nodes, key=lambda n: n.y())

            n = len(nodes_sorted)
            start_y = base_y - (n - 1) * dy / 2

            for i, node in enumerate(nodes_sorted):
                new_y = start_y + i * dy
                node.setPos(x, new_y)


# ==================================
# View：ズーム/パン（Scene操作を邪魔しない）
# ==================================
class GraphicsView(QtWidgets.QGraphicsView):
    """ホイールズーム、Ctrl+ドラッグ or 中ボタンでパン（通常操作はSceneへ渡す）"""

    MIN_ZOOM_SCALE = 0.08
    MAX_ZOOM_SCALE = 3.0

    def __init__(self, scene, parent=None):
        """ズーム・パン操作付きの View を初期化する。"""
        super().__init__(scene, parent)

        self.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        self._default_drag_mode = QtWidgets.QGraphicsView.DragMode.RubberBandDrag
        self.setDragMode(self._default_drag_mode)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._panning = False
        self._ctrl_down = False
        self._pan_start = QtCore.QPoint()

        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # 初期表示時の倍率
        self.scale(INITIAL_VIEW_SCALE, INITIAL_VIEW_SCALE)

    def _effective_min_zoom_scale(self) -> float:
        """シーン全体を表示できる倍率を考慮した最小倍率を返す。"""
        scene = self.scene()
        if scene is None:
            return self.MIN_ZOOM_SCALE

        rect = scene.sceneRect()
        vp = self.viewport().rect()
        if rect.isNull() or vp.width() <= 0 or vp.height() <= 0:
            return self.MIN_ZOOM_SCALE

        fit_scale = min(vp.width() / rect.width(), vp.height() / rect.height())
        # 全体表示に必要な倍率より少しだけ小さい所まで許可して、操作の余裕を残す
        return min(self.MIN_ZOOM_SCALE, fit_scale * 0.95)

    # ---------- Zoom ----------
    def wheelEvent(self, event: QtGui.QWheelEvent):
        """ホイールズーム"""
        zoom = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15

        current_scale = self.transform().m11()
        target_scale = current_scale * zoom
        min_scale = self._effective_min_zoom_scale()

        if target_scale < min_scale:
            zoom = min_scale / current_scale
        elif target_scale > self.MAX_ZOOM_SCALE:
            zoom = self.MAX_ZOOM_SCALE / current_scale

        self.scale(zoom, zoom)

    # ---------- Ctrl key ----------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Ctrl押下中だけパンモード（カーソル変更）"""
        if event.key() == QtCore.Qt.Key.Key_Control and not event.isAutoRepeat():
            self._ctrl_down = True
            self.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        """Ctrl解除で通常カーソルへ"""
        if event.key() == QtCore.Qt.Key.Key_Control and not event.isAutoRepeat():
            self._ctrl_down = False
            if not self._panning:
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)

    # ---------- Mouse ----------
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """パン開始条件だけViewが奪い、それ以外はSceneへ渡す"""
        ctrl_pressed = bool(event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier)
        if event.button() == QtCore.Qt.MouseButton.MiddleButton or (
            event.button() == QtCore.Qt.MouseButton.LeftButton and (self._ctrl_down or ctrl_pressed)
        ):
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            self.setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """パン中はスクロールバーで移動、通常はSceneへ"""
        if self._panning:
            pos = event.position().toPoint()
            delta = pos - self._pan_start
            self._pan_start = pos

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        """パン終了でRubberBandに戻す"""
        if self._panning:
            self._panning = False
            self.setDragMode(self._default_drag_mode)
            self.setCursor(
                QtCore.Qt.CursorShape.OpenHandCursor
                if self._ctrl_down
                else QtCore.Qt.CursorShape.ArrowCursor
            )
            event.accept()
            return

        super().mouseReleaseEvent(event)


# ==================================
# MainWindow：ツールバー/Undo/ショートカット
# ==================================
class MainWindow(QtWidgets.QMainWindow):
    """PyEditor のメインウィンドウ。"""

    def __init__(self):
        """メインウィンドウとツールバーを初期化する。"""
        super().__init__()
        self.setWindowTitle(gui_text("scn_main_title"))
        self.resize(900, 600)

        # Undoスタック（Ctrl+Z/Y）
        self.undo_stack = QtGui.QUndoStack(self)

        # Scene/View（編集の中心）
        self.scene = GraphScene(self.undo_stack, self)
        self.view = GraphicsView(self.scene, self)
        self.setCentralWidget(self.view)

        # ---- Toolbar（主要操作を1クリック化） ----
        toolbar = self.addToolBar(gui_text("scn_toolbar_name"))
        toolbar.setMovable(False)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        toolbar.addWidget(spacer)

        # toolbar.addAction("保存 (PNG)", lambda: self.scene.save_png("state_graph_qt.png"))
        toolbar.addAction(gui_text("scn_toolbar_save"), lambda: self.scene.export_json("state_graph.json"))
        toolbar.addAction(gui_text("scn_toolbar_load"), self.confirm_and_load_json)
        toolbar.addAction(gui_text("scn_toolbar_align"), self.scene.auto_layout)

        # 見た目（ボタン風）
        toolbar.setStyleSheet("""
            QToolBar {
                background: #f5f7fb;
                border-bottom: 1px solid #d0d7e2;
                spacing: 6px;
                padding: 4px 8px;
            }
            QToolButton {
                background: #87ceeb;
                border: 1px solid #c5cfdd;
                border-radius: 12px;
                padding: 2px 8px;
                margin: 0 2px;
                color: #1b2b3a;
                font-size: 10pt;
            }
            QToolButton:hover {
                background: #e8f2ff;
                border-color: #6b9cff;
            }
            QToolButton:pressed {
                background: #d6e4ff;
                border-color: #2d6cff;
            }
        """)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)

        # Undo / Redo（ツールバー + ショートカット）
        act_undo = toolbar.addAction(gui_text("scn_toolbar_undo"))
        act_undo.triggered.connect(self.undo_stack.undo)
        act_undo.setShortcut(QtGui.QKeySequence.StandardKey.Undo)

        act_redo = toolbar.addAction(gui_text("scn_toolbar_redo"))
        act_redo.triggered.connect(self.undo_stack.redo)
        act_redo.setShortcut(QtGui.QKeySequence.StandardKey.Redo)

        # ---- StatusBar（操作ヒント） ----
        hint = QtWidgets.QLabel(gui_text("scn_status_hint"))
        hint.setStyleSheet("color: #ffffff; padding: 4px;")
        statusbar = self.statusBar()
        statusbar.setStyleSheet("background: #4682b4;")
        statusbar.addWidget(hint)

    def load_json_file(self, path: str):
        """外部起動用JSONロード（例外は呼び元に投げる）"""

        print(f"auto loading: {path}")

        self.scene.import_json(path)

    def confirm_and_load_json(self):
        """ロード前に確認ダイアログを表示し、OK時のみ読み込む"""
        msg = gui_text("msg_scn_load_confirm")
        reply = QtWidgets.QMessageBox.question(
            self,
            gui_text("msg_warn_confirm"),
            msg,
            QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Ok:
            self.scene.import_json("state_graph.json")

    def keyPressEvent(self, event):
        """Delete=削除 / Esc=選択解除"""
        if event.key() == QtCore.Qt.Key.Key_Delete:
            self.scene.delete_selected()
        elif event.key() == QtCore.Qt.Key.Key_Escape:
            self.scene.clearSelection()
        else:
            super().keyPressEvent(event)


# =========================
# エントリポイント
# =========================
def main():
    """PyEditorを起動し、必要に応じてJSONを初期ロードする。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "json_path",
        nargs="?",
        default=None,
        help="Path to scenario JSON file to load on startup",
    )
    parser.add_argument(
        "--lang",
        choices=["ja", "en"],
        type=str,
        default="ja",
        help="Language type: ja/en",
    )
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)

    # GUI表示テキストデータを取得
    read_gui_text_data(lang=args.lang)

    # -----------------------------
    #  起動引数の取得
    # -----------------------------
    json_path = args.json_path

    w = MainWindow()

    # -----------------------------
    #  JSON引数が来ていれば自動ロード
    # -----------------------------
    if json_path:
        try:
            w.load_json_file(json_path)   # ←既存の読込関数を呼ぶだけ
            w.undo_stack.clear()          # 起動時ロード状態をUndoの基準点にする
        except Exception as e:
            print(e)

    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

