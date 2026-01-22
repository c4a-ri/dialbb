from PySide6 import QtCore, QtGui, QtWidgets
import sys
import os
import json
import uuid
from collections import deque

# =========================
# 定数：見た目・サイズ設定
# =========================

# ノードサイズ（固定レイアウト方針）
NODE_W = 140                 # ノード幅
NODE_H = 200                 # （未使用枠：共通の高さなどに使える）
NODE_H_SYSTEM = 160          # Systemノードの固定高さ
NODE_H_USER   = 260          # Userノードの固定高さ

# QTextEdit高さ（ノード内の表示用：スクロール無しで収まる前提）
SYS_UTTERANCE_H = 35         # System発話
USR_CONDITION_H = 40         # User条件
USR_ACTION_H    = 30         # Userアクション

# ノードの角丸・ヘッダ
NODE_CORNER_R = 12           # ノード角丸
NODE_HEADER_H = 34           # ヘッダー高さ

# コネクタ
CONNECTOR_R = 6              # コネクタ半径（円）

# boundingRectの余白（影・選択枠・アンチエイリアス用）
SHADOW_DX = 2
SHADOW_DY = 3
PAD = 8                      # 選択枠 + AA分の余白
CONNECTOR_OUTSIDE = -6       # コネクタを外側に出す量（マイナスで外へ）

# node types
NODE_TYPE_SYSTEM = "system"
NODE_TYPE_USER = "user"


# ==================================
# ノード編集ダイアログ（モーダル）
# ==================================
class NodeEditDialog(QtWidgets.QDialog):
    def __init__(self, node: "NodeItem", parent=None):
        super().__init__(parent)
        self.node = node
        self.setModal(True)
        self.setWindowTitle(node.node_type)

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
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        # System用フォーム
        if self.node.node_type == NODE_TYPE_SYSTEM:
            # ノードタイプ: Combo
            self.node_kind = QtWidgets.QComboBox()
            self.node_kind.addItems(["initial", "名前を言った", "食べる", "好き", "final"])
            self.node_kind.setMinimumWidth(240)

            # 発話: Text
            self.utterance = QtWidgets.QTextEdit()
            self.utterance.setMinimumHeight(120)

            form.addRow("ノードタイプ:", self.node_kind)
            form.addRow("発話:", self.utterance)

        # User用フォーム
        else:
            # 優先度: SpinBox
            self.priority = QtWidgets.QSpinBox()
            self.priority.setRange(0, 10**9)
            self.priority.setMinimumWidth(120)

            # ユーザ発話タイプ: Text
            self.utterance_type = QtWidgets.QTextEdit()
            self.utterance_type.setMinimumHeight(60)

            # 遷移条件: Text
            self.condition = QtWidgets.QTextEdit()
            self.condition.setMinimumHeight(140)

            # 遷移時アクション: Text
            self.action = QtWidgets.QTextEdit()
            self.action.setMinimumHeight(80)

            form.addRow("優先度（0以上の整数）:", self.priority)
            form.addRow("ユーザ発話タイプ:", self.utterance_type)
            form.addRow("遷移の条件:", self.condition)
            form.addRow("遷移時のアクション（上級者用）:", self.action)

        root.addLayout(form)
        root.addStretch(1)

        # ---- buttons（保存/キャンセル） ----
        btns = QtWidgets.QDialogButtonBox()
        btn_cancel = btns.addButton("キャンセル", QtWidgets.QDialogButtonBox.RejectRole)
        btn_ok = btns.addButton("保存", QtWidgets.QDialogButtonBox.AcceptRole)
        btn_ok.setFocusPolicy(QtCore.Qt.StrongFocus)
        btn_cancel.setFocusPolicy(QtCore.Qt.StrongFocus)

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)

        # ---- Tab操作：入力→次の入力へ ----
        # QTextEditのTabキーを「Tab文字入力」ではなく「次の入力へ」にする
        if self.node.node_type == NODE_TYPE_SYSTEM:
            self.utterance.setTabChangesFocus(True)
        else:
            self.utterance_type.setTabChangesFocus(True)
            self.condition.setTabChangesFocus(True)
            self.action.setTabChangesFocus(True)

        # ---- Tab順序：このダイアログ内だけで完結させる ----
        widgets = []
        if self.node.node_type == NODE_TYPE_SYSTEM:
            widgets = [self.node_kind, self.utterance]
        else:
            widgets = [self.priority, self.utterance_type, self.condition, self.action]

        for w in widgets:
            w.setFocusPolicy(QtCore.Qt.StrongFocus)

        btn_cancel.setFocusPolicy(QtCore.Qt.StrongFocus)
        btn_ok.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Tab順（同一Dialog内のみ）
        if self.node.node_type == NODE_TYPE_SYSTEM:
            QtWidgets.QWidget.setTabOrder(self.node_kind, self.utterance)
            QtWidgets.QWidget.setTabOrder(self.utterance, btn_cancel)
            QtWidgets.QWidget.setTabOrder(btn_cancel, btn_ok)
            self.node_kind.setFocus()  # 初期フォーカス
        else:
            QtWidgets.QWidget.setTabOrder(self.priority, self.utterance_type)
            QtWidgets.QWidget.setTabOrder(self.utterance_type, self.condition)
            QtWidgets.QWidget.setTabOrder(self.condition, self.action)
            QtWidgets.QWidget.setTabOrder(self.action, btn_cancel)
            QtWidgets.QWidget.setTabOrder(btn_cancel, btn_ok)
            self.priority.setFocus()   # 初期フォーカス

        root.addWidget(btns)

    def _load_from_node(self):
        """ノード→ダイアログへ値を反映"""
        if self.node.node_type == NODE_TYPE_SYSTEM:
            kind = self.node.get_field("node_kind") or "initial"
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

            self.utterance_type.setPlainText(self.node.get_field("utterance_type"))
            self.condition.setPlainText(self.node.get_field("condition"))
            self.action.setPlainText(self.node.get_field("action"))

    def apply_to_node(self):
        """ダイアログ→ノードへ値を反映（OK時に呼ぶ）"""
        if self.node.node_type == NODE_TYPE_SYSTEM:
            self.node.set_field("node_kind", self.node_kind.currentText())
            self.node.set_field("utterance", self.utterance.toPlainText())
        else:
            self.node.set_field("priority", str(self.priority.value()))
            self.node.set_field("utterance_type", self.utterance_type.toPlainText())
            self.node.set_field("condition", self.condition.toPlainText())
            self.node.set_field("action", self.action.toPlainText())


# =========================
# コネクタ（ノードの接続点）
# =========================
class ConnectorItem(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent_node, name, x, y):
        super().__init__(-CONNECTOR_R, -CONNECTOR_R, CONNECTOR_R * 2, CONNECTOR_R * 2)
        self.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
        self.setPen(QtGui.QPen(QtGui.QColor("#333333")))
        self.setZValue(2)
        self.name = name
        self.node = parent_node
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)

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
        super().__init__()
        self.from_conn = from_connector
        self.to_conn = to_connector

        pen = QtGui.QPen(QtGui.QColor("#000000"))
        pen.setWidth(2)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        pen.setJoinStyle(QtCore.Qt.RoundJoin)
        self.setPen(pen)
        self.setZValue(0)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)

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

    def shape(self) -> QtGui.QPainterPath:
        """選択しやすいように当たり判定だけ太くする"""
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(self.HIT_STROKE_WIDTH)
        stroker.setCapStyle(QtCore.Qt.RoundCap)
        stroker.setJoinStyle(QtCore.Qt.RoundJoin)
        return stroker.createStroke(self.path())

    def itemChange(self, change, value):
        """選択時は色/太さを変えて視認性UP"""
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
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
    def __init__(self, x, y, text="State", node_id=None, node_type=NODE_TYPE_USER):
        super().__init__()

        # ノード基本情報（固定サイズ方針）
        self.node_w = NODE_W
        self.node_h = NODE_H_SYSTEM if node_type == NODE_TYPE_SYSTEM else NODE_H_USER
        self.node_id = node_id or str(uuid.uuid4())
        self.node_type = node_type

        # 選択/移動ができるGraphicsItem
        self.setZValue(1)
        self.setPos(x, y)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

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
    def paint(self, painter: QtGui.QPainter, option, widget=None):
        """ノードのカード風描画（影/本体/ヘッダー/IDバッジ/選択枠）"""
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        r = self.boundingRect()

        # 影
        shadow = QtCore.QRectF(r)
        shadow.translate(2, 3)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 40))
        painter.drawRoundedRect(shadow, NODE_CORNER_R, NODE_CORNER_R)

        # 本体
        painter.setBrush(self.body_color)
        painter.setPen(QtGui.QPen(self.border_color, 2))
        painter.drawRoundedRect(r, NODE_CORNER_R, NODE_CORNER_R)

        # ヘッダー
        header = QtCore.QRectF(r.left(), r.top(), r.width(), NODE_HEADER_H)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(self.header_color)
        painter.drawRoundedRect(header, NODE_CORNER_R, NODE_CORNER_R)

        # ヘッダー下ライン
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 40), 1))
        painter.drawLine(header.bottomLeft(), header.bottomRight())

        # IDバッジ（右上）
        short_id = str(self.node_id)[:8]
        badge_text = f"id:{short_id}"
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
        painter.drawText(badge_rect, QtCore.Qt.AlignCenter, badge_text)

        # 選択枠
        if self.isSelected():
            sel_pen = QtGui.QPen(QtGui.QColor("#2d6cff"), 3)
            sel_pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(sel_pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), NODE_CORNER_R, NODE_CORNER_R)

    # ---- ノード内のフォーム表示（ProxyWidget） ----
    def _build_form(self):
        """ノード内に「読み取り専用フォーム」を固定配置で載せる（編集はダイアログ）"""
        if hasattr(self, "form_proxy") and self.form_proxy is not None:
            self.scene().removeItem(self.form_proxy) if self.scene() else None
            self.form_proxy = None

        self.form_widget = QtWidgets.QWidget()
        self.form_widget.setObjectName("nodeForm")

        # レイアウト（フォーム外枠の余白）
        v = QtWidgets.QVBoxLayout(self.form_widget)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)

        # ノードタイプ別：フォーム項目を固定で構築
        if self.node_type == NODE_TYPE_SYSTEM:
            self._add_labeled_line(v, "ノードタイプ", "initial", key="node_kind")
            self._add_labeled_text(v, "発話", "", key="utterance", min_h=SYS_UTTERANCE_H)
        else:
            self._add_labeled_line(v, "優先度", "", key="priority")
            self._add_labeled_line(v, "発話タイプ", "", key="utterance_type")
            self._add_labeled_text(v, "遷移の条件", "", key="condition", min_h=USR_CONDITION_H)
            self._add_labeled_line(v, "遷移時のアクション", "", key="action")

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
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            for e in list(self.edges):
                e.update_positions()
        return super().itemChange(change, value)

    # ---- title edit ----
    def set_label(self, text):
        """ヘッダータイトルの更新"""
        self.title_item.setText(text)
        self._layout_texts()

    # ---- form field access (JSON/ダイアログ連携用) ----
    def get_field(self, key: str) -> str:
        """フォーム値取得（QLineEdit/QTextEditをキーで取得）"""
        w = self.form_widget.findChild(QtWidgets.QWidget, key)
        if isinstance(w, QtWidgets.QLineEdit):
            return w.text()
        if isinstance(w, QtWidgets.QTextEdit):
            return w.toPlainText()
        return ""

    def set_field(self, key: str, value: str):
        """フォーム値設定（表示更新・JSON読み込み用）"""
        w = self.form_widget.findChild(QtWidgets.QWidget, key)
        if isinstance(w, QtWidgets.QLineEdit):
            w.setText(value or "")
        elif isinstance(w, QtWidgets.QTextEdit):
            w.setPlainText(value or "")


# ==================================
# Undo/Redo：Sceneスナップショットコマンド
# ==================================
class GraphHistoryCommand(QtGui.QUndoCommand):
    """Scene全体の before/after を保存して Undo/Redo する（スナップショット方式）"""

    def __init__(self, scene, before_state: dict, after_state: dict, description: str):
        super().__init__(description)
        self.scene = scene
        self.before_state = before_state
        self.after_state = after_state
        self._first = True  # push直後のredoは「現状維持」になるのでスキップ

    def undo(self):
        self.scene._load_state_from_dict(self.before_state)

    def redo(self):
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
    def __init__(self, undo_stack: QtGui.QUndoStack | None = None, parent=None):
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

    def _find_ancestor_item(self, item):
        """Proxy内の子Widget等からでも Node/Connector を拾うための親たどり"""
        while item is not None and not isinstance(item, (NodeItem, ConnectorItem)):
            item = item.parentItem()
        return item

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

        if isinstance(item, NodeItem):
            if self.undo_stack is not None:
                before = self._state_to_dict()
                dlg = NodeEditDialog(item)
                if dlg.exec() == QtWidgets.QDialog.Accepted:
                    dlg.apply_to_node()
                    after = self._state_to_dict()
                    self.undo_stack.push(GraphHistoryCommand(self, before, after, "ノード編集"))
            else:
                dlg = NodeEditDialog(item)
                if dlg.exec() == QtWidgets.QDialog.Accepted:
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
            pen.setStyle(QtCore.Qt.DashLine)
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
        if self.temp_line is not None and hasattr(self, "_drag_start"):
            p1 = self._drag_start.center_scene_pos()
            p2 = event.scenePos()
            self.temp_line.setLine(p1.x(), p1.y(), p2.x(), p2.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """解放：エッジ確定 or ノード移動のUndo確定"""
        # エッジ作成ドラッグ終了
        if self.temp_line is not None and hasattr(self, "_drag_start"):
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
            del self._drag_start
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
            self._create_edge_raw(from_conn, to_conn)
        self._push_history("エッジ追加", do)

    def delete_selected(self):
        """選択中のノード/エッジを削除（履歴つき）"""
        def do():
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

        menu = QtWidgets.QMenu()

        # 空白：System/User追加
        if item is None:
            act_sys = menu.addAction("Systemとして追加")
            act_user = menu.addAction("Userとして追加")
            menu.addSeparator()
            act_cancel = menu.addAction("キャンセル")

            chosen = menu.exec(event.screenPos())
            if chosen == act_sys:
                def do():
                    node = NodeItem(pos.x(), pos.y(), text="システム", node_type=NODE_TYPE_SYSTEM)
                    self.addItem(node)
                    self.nodes.append(node)
                self._push_history("Systemノード追加", do)

            elif chosen == act_user:
                def do():
                    node = NodeItem(pos.x(), pos.y(), text="ユーザ", node_type=NODE_TYPE_USER)
                    self.addItem(node)
                    self.nodes.append(node)
                self._push_history("Userノード追加", do)

            event.accept()
            return

        # ノード：ラベル編集 /（Systemのみ）配下User整列 / 削除
        if isinstance(item, NodeItem):
            act_edit = menu.addAction("ラベル編集")

            act_align = None
            if item.node_type == NODE_TYPE_SYSTEM:
                act_align = menu.addAction("接続先Userを優先度順に縦整列")

            act_del = menu.addAction("削除")
            menu.addSeparator()
            act_cancel = menu.addAction("キャンセル")

            chosen = menu.exec(event.screenPos())

            if chosen == act_edit:
                text, ok = QtWidgets.QInputDialog.getText(
                    None, "ラベル編集", "ラベルを入力:", text=item.title_item.text()
                )
                if ok and text is not None:
                    item.set_label(text)

            elif act_align and chosen == act_align:
                self.align_users_under_system(item)

            elif chosen == act_del:
                self.remove_node(item)

            event.accept()
            return

        # エッジ：削除
        if isinstance(item, EdgeItem):
            act_del = menu.addAction("削除")
            chosen = menu.exec(event.screenPos())
            if chosen == act_del:
                self.remove_edge(item)
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
                    "utterance_type": n.get_field("utterance_type"),
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
            self.addItem(node)
            self.nodes.append(node)
            id_map[node.node_id] = node

            # フィールド復元
            if node.node_type == NODE_TYPE_SYSTEM:
                node.set_field("node_kind", n.get("node_kind", ""))
                node.set_field("utterance", n.get("utterance", ""))
            else:
                node.set_field("priority", str(n.get("priority", "")))
                node.set_field("utterance_type", n.get("utterance_type", ""))
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

    def _push_history(self, description: str, mutate_func):
        """操作前後のスナップショットを取り、UndoStackへ積む共通関数"""
        if self.undo_stack is None:
            mutate_func()
            return

        before = self._state_to_dict()
        mutate_func()
        after = self._state_to_dict()

        self.undo_stack.push(GraphHistoryCommand(self, before, after, description))

    # ---------- JSON export/import ----------
    def export_json(self, path):
        """現在の状態をJSONへ保存"""
        data = self._state_to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        QtWidgets.QMessageBox.information(
            None, "エクスポート", f"{os.path.abspath(path)} にエクスポートしました"
        )

    def import_json(self, path):
        """JSONから復元（インポートも履歴に乗せる）"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            def do():
                self._load_state_from_dict(data)

            self._push_history("JSONインポート", do)

            QtWidgets.QMessageBox.information(
                None, "インポート", f"{os.path.abspath(path)} を読み込みました"
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(None, "インポートエラー", str(exc))

    # ---------- PNG export ----------
    def save_png(self, path):
        """Sceneの見えている内容をPNGで保存"""
        rect = self.itemsBoundingRect()
        if rect.isNull():
            QtWidgets.QMessageBox.warning(None, "保存", "保存する内容がありません")
            return

        margin = 20
        rect = rect.adjusted(-margin, -margin, margin, margin)

        scale = 2.0
        w = max(1, int(rect.width() * scale))
        h = max(1, int(rect.height() * scale))

        img = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
        img.fill(QtGui.QColor("white"))

        painter = QtGui.QPainter(img)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)

        target = QtCore.QRectF(0, 0, w, h)
        self.render(painter, target, rect)
        painter.end()

        img.save(path)
        QtWidgets.QMessageBox.information(None, "保存", f"{os.path.abspath(path)} に保存しました")

    # ---------- layout helpers：部分整列 / 全体整列 ----------
    def align_users_under_system(self, system_node: NodeItem):
        """Systemの接続先Userを priority（降順）で縦整列（System右側へ配置）"""
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

    def _auto_layout_impl(self):
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
        base_x = 0.0
        base_y = 0.0
        dy = LAYOUT_DY

        for lv in sorted(levels.keys()):
            nodes = levels[lv]
            x = base_x + lv * LAYOUT_DX

            # User層は priority、その他は現Y順（元の上下関係を維持）
            if all(n.node_type == NODE_TYPE_USER for n in nodes):
                def priority_of(node: NodeItem) -> int:
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
    """ホイールズーム、Space+ドラッグ or 中ボタンでパン（通常操作はSceneへ渡す）"""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setRenderHint(QtGui.QPainter.TextAntialiasing, True)

        self._default_drag_mode = QtWidgets.QGraphicsView.RubberBandDrag
        self.setDragMode(self._default_drag_mode)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)

        self._panning = False
        self._space_down = False
        self._pan_start = QtCore.QPoint()

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    # ---------- Zoom ----------
    def wheelEvent(self, event: QtGui.QWheelEvent):
        """ホイールズーム"""
        zoom = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom, zoom)

    # ---------- Space key ----------
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """Space押下中だけパンモード（カーソル変更）"""
        if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = True
            self.setCursor(QtCore.Qt.OpenHandCursor)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        """Space解除で通常カーソルへ"""
        if event.key() == QtCore.Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = False
            if not self._panning:
                self.setCursor(QtCore.Qt.ArrowCursor)
            event.accept()
            return
        super().keyReleaseEvent(event)

    # ---------- Mouse ----------
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """パン開始条件だけViewが奪い、それ以外はSceneへ渡す"""
        if event.button() == QtCore.Qt.MiddleButton or (
            event.button() == QtCore.Qt.LeftButton and self._space_down
        ):
            self._panning = True
            self._pan_start = event.position().toPoint()
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
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
            self.setCursor(QtCore.Qt.OpenHandCursor if self._space_down else QtCore.Qt.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)


# ==================================
# MainWindow：ツールバー/Undo/ショートカット
# ==================================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DialBBシナリオエディタ (PySide6)")
        self.resize(900, 600)

        # Undoスタック（Ctrl+Z/Y）
        self.undo_stack = QtGui.QUndoStack(self)

        # Scene/View（編集の中心）
        self.scene = GraphScene(self.undo_stack, self)
        self.view = GraphicsView(self.scene, self)
        self.setCentralWidget(self.view)

        # ---- Toolbar（主要操作を1クリック化） ----
        toolbar = self.addToolBar("tools")
        toolbar.setMovable(False)

        toolbar.addAction("保存 (PNG)", lambda: self.scene.save_png("state_graph_qt.png"))
        toolbar.addAction("エクスポート JSON", lambda: self.scene.export_json("state_graph.json"))
        toolbar.addAction("インポート JSON", lambda: self.scene.import_json("state_graph.json"))
        toolbar.addAction("整列", self.scene.auto_layout)

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
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)

        # Undo / Redo（ツールバー + ショートカット）
        act_undo = toolbar.addAction("元に戻す")
        act_undo.triggered.connect(self.undo_stack.undo)
        act_undo.setShortcut(QtGui.QKeySequence.Undo)

        act_redo = toolbar.addAction("やり直し")
        act_redo.triggered.connect(self.undo_stack.redo)
        act_redo.setShortcut(QtGui.QKeySequence.Redo)

        # ---- StatusBar（操作ヒント） ----
        hint = QtWidgets.QLabel(
            "操作: 右クリック=追加/編集,  ダブルクリック=ノード編集,  "
            "コネクタドラッグ=接続,  Delete=削除,  Ctrl+Z/Y=Undo/Redo,  "
            "ホイール=ズーム,  中ボタン or Space+ドラッグ=パン"
        )
        hint.setStyleSheet("color: #ffffff; padding: 4px;")
        statusbar = self.statusBar()
        statusbar.setStyleSheet("background: #4682b4;")
        statusbar.addWidget(hint)

        # キャンバス（パン可能範囲）
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)

    def keyPressEvent(self, event):
        """Delete=削除 / Esc=選択解除"""
        if event.key() == QtCore.Qt.Key_Delete:
            self.scene.delete_selected()
        elif event.key() == QtCore.Qt.Key_Escape:
            self.scene.clearSelection()
        else:
            super().keyPressEvent(event)


# =========================
# エントリポイント
# =========================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
