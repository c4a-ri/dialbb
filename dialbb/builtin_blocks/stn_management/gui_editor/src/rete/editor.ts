import { AreaPlugin, AreaExtensions } from "rete-area-plugin";
import { VuePlugin, Presets as VuePresets } from 'rete-vue-plugin';
import type { VueArea2D } from 'rete-vue-plugin';
import { NodeEditor, ClassicPreset } from "rete";
import type { GetSchemes } from "rete";
import { DataflowEngine } from "rete-engine";
import {
  ConnectionPlugin,
  ClassicFlow,
  getSourceTarget,
  Presets as ConnectionPresets
} from "rete-connection-plugin";
import {
  AutoArrangePlugin,
  Presets as ArrangePresets,
  ArrangeAppliers
} from "rete-auto-arrange-plugin";
//} from "rete-context-menu-plugin";
import { ContextMenuPlugin, Presets as ContextMenuPresets
} from "./context-menu-plugin";
import type { ContextMenuExtra } from "./context-menu-plugin";
import type { HistoryActions } from "rete-history-plugin";
import {
  HistoryPlugin,
  HistoryExtensions,
  Presets as HistoryPresets
 } from "rete-history-plugin";
 
import { easeInOut } from "popmotion";
import { insertableNodes } from "./insert-node";
import { exportGraph } from "./outputData";

import { Modules } from "./modules";
import {
  systemNode,
  userNode
} from "./nodes";
import { clearEditor } from "./utils";
import { createNode, importEditor } from "./import";
import rootModule from "../data/base.json";

import SystemNode from "./nodes/systemNode.vue";
import UserNode from "./nodes/userNode.vue";
import CustomControl from "./nodes/CustomControl.vue";
import { CustomInputControl } from "./utils";
import ShortControl from "./nodes/ShortControl.vue";
import SelectableConnection from "./nodes/SelectableConnection.vue";

type Node = systemNode | userNode;

export class Connection<
  N extends Node
> extends ClassicPreset.Connection<N, N> {
  selected?: boolean;
}

export type Schemes = GetSchemes<
  Node, Connection<Node>
>;

const socket = new ClassicPreset.Socket("socket");
type AreaExtra = VueArea2D<Schemes> | ContextMenuExtra;

export type Context = {
  process: () => void;
  editor: NodeEditor<Schemes>;
  area: AreaPlugin<Schemes, any>;
  modules: Modules<Schemes>;
  engine: DataflowEngine<Schemes>;
};

let contextG: any;


/*--------------------------------------------------
  Create Node Editor.
--------------------------------------------------*/
export async function createEditor(container: HTMLElement) {
  const editor = new NodeEditor<Schemes>();
  const area = new AreaPlugin<Schemes, AreaExtra>(container);
  const connection = new ConnectionPlugin<Schemes, AreaExtra>();
  const render = new VuePlugin<Schemes, AreaExtra>();
  const arrange = new AutoArrangePlugin<Schemes, AreaExtra>();
  const engine = new DataflowEngine<Schemes>();
  const history = new HistoryPlugin<Schemes, HistoryActions<Schemes>>();

  // 選択可能なノードにする
  AreaExtensions.selectableNodes(area, AreaExtensions.selector(), {
    accumulating: AreaExtensions.accumulateOnCtrl()
  });
  
  editor.use(engine)

  function process() {
    engine.reset();

    editor
      .getNodes()
      .filter((n) => n instanceof userNode)
      .forEach((n) => engine.fetch(n.id));
  }

  /* ユーザ接続のconnectionはdefault　Objectになるので
     ClassicPreset.Connectionで生成するようにoverwrite.
  */
  // これdefault：connection.addPreset(ConnectionPresets.classic.setup());
  connection.addPreset(() => new ClassicFlow({
    makeConnection(from, to, context) {
      const [source, target] = getSourceTarget(from, to) || [null, null];
      const { editor } = context;
      if (source && target) {
        // console.log('addConnection:'+source.key+'==>'+target.key)
        editor.addConnection(
          new Connection(
            editor.getNode(source.nodeId),
            source.key as never,
            editor.getNode(target.nodeId),
            target.key as never
          )
        );
        return true; // ensure that the connection has been successfully added
      }
    }
  }))

  // render.addPreset(VuePresets.classic.setup()); ※無効にしないとCustomNodeのcssが効かない
  render.addPreset(VuePresets.contextMenu.setup());
  render.addPreset(
    // カスタマイズしたパーツの定義
    VuePresets.classic.setup({
      customize: {
        node(context) {
          // console.log(context.payload, CustomNode);
          if (context.payload.label === "systemNode") {
            return SystemNode;   // Systemのノード
          }
          else if (context.payload.label === "userNode") {
            return UserNode;     // Userのノード
          }
          return VuePresets.classic.Node;
        },
        control(context) {
          if (context.payload !== null) {
            // console.table(context.payload)
            if (context.payload instanceof CustomInputControl) {
              if (context.payload.label == 'utterance') {
                return CustomControl;   // textAreaのコントロール
              }
              else if (context.payload.type == 'number'
                       && context.payload.label == '') {
                return ShortControl;    // 幅が短いコントロール
              }
              else {
                return VuePresets.classic.Control;
              }
            }
            else {
              return VuePresets.classic.Control;
            }
          }
        },
        connection(context) {
          return SelectableConnection;
        }
      }
    })
  );

  editor.use(area);
  area.use(connection);
  area.use(render);

  // ノードの自動整列を登録
  arrange.addPreset(ArrangePresets.classic.setup());
  area.use(arrange);

  // アンドゥ機能の登録
  history.addPreset(HistoryPresets.classic.setup());
  HistoryExtensions.keyboard(history);
  area.use(history);


  // コンテキストメニューの定義
  const contextMenu = new ContextMenuPlugin<Schemes>({
    items: ContextMenuPresets.classic.setup([
      ["Add SystemNode", () => createNode(context, "systemNode", null)],
      ["Add UserNode", () => createNode(context, "userNode", null)],
    ])
  });
  area.use(contextMenu);

  // Create module
  const modules = new Modules<Schemes>(
    async (data, editor) => {
      //data = rootModule;

      if (!data) throw new Error("cannot find module");
      await importEditor(
        context,
        data
      );
    }
  );
  const context: Context = {
    process,
    editor,
    area,
    modules,
    engine
  };

  contextG = context;

  const animatedApplier = new ArrangeAppliers.TransitionApplier<Schemes, never>(
    {
      duration: 500,
      timingFunction: easeInOut
    }
  );

  AreaExtensions.simpleNodesOrder(area);

  // ★インサートモードは無効にする
  // insertableNodes(area, {
  //   async createConnections(node, connection) {
  //     await editor.addConnection(
  //       new Connection(
  //         editor.getNode(connection.source),
  //         connection.sourceOutput,
  //         node,
  //         "state"
  //       )
  //     );
  //     await editor.addConnection(
  //       new Connection(
  //         node,
  //         "next",
  //         editor.getNode(connection.target),
  //         connection.targetInput
  //       )
  //     );
  //     arrange.layout({
  //       applier: animatedApplier
  //     });
  //   }
  // });

  // --------------------------
  // initial drawing
  // --------------------------
  async function openModule(data: any = null) {
    if (!data) {
      console.log('Initial openModule!');
      data = rootModule;
    }

    await clearEditor(editor);

    const module = modules.findModule(data);
    if (module) {
      // Node描画
      await module.apply(editor);
    }

    await arrange.layout({
      options: {
        'elk.layered.nodePlacement.strategy': 'SIMPLE',
      },
      applier: animatedApplier
    });

    AreaExtensions.zoomAt(area, editor.getNodes());

    // 発話タイプ一覧を親コンポーネントに渡す
    return data["types"]
  }

  (window as any).area = area;
  
  // --------------------------
  // Reset Editor
  // --------------------------
  async function resetEditor() {
    console.log('Call resetEditor()')
    await clearEditor(editor);
  }

  // --------------------------
  // NodeデータExport
  // --------------------------
  async function saveModule(dev: boolean, filePath: string) {
    console.log('Call saveModule() dev:'+dev+' File='+filePath)
    // NodeをJSONにシリアライズ
    const data = await exportGraph(context.editor);
    console.table(data)
    // エラーチェック
    if ('warning' in data) {
      // エラー終了
      return data;
    }

    const datastring = JSON.stringify(data);
    // console.log('Write data :'+datastring);
    if (dev) {
      // devモードの時はファイルをダウンロード
      const blob = new Blob([datastring], {type: "application/json"});
      let link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'node-data.json';
      link.click();
    }
    else {
      // ファイルに保存
      const file = new File([datastring], 'save.json', {type: "application/json"});
      const formData = new FormData();
      formData.append('file', file);

      try {
        // サーバに保存リクエスト送信(POST)
        const response = await fetch('/save', {
          method: 'POST',
          body: formData
        });
        if (!response.ok) {
          throw new Error('Upload failed');
        }

        // レスポンスのJSONを取得
        const responseData = await response.json();
        console.table(responseData);
        // const msg = JSON.stringify(responseData.text);
        if (responseData.message && responseData.message != '') {
          alert(responseData.message);
        }
      }
      catch (error: any) {
        console.error(error.message);
      }
    }
    return {};
  }

  return {
    resetEditor,
    openModule,
    saveModule,
    destroy: () => {
      console.log("area.destroy1", area.nodeViews.size);
      area.destroy();
    }
  };
}


// --------------------------
// Nodeデータ入力Dialogの[Save]が実行された時に起動
// --------------------------
export async function saveNodeValue(nodeid: string = '', setVal: any = {}) {
  if (nodeid == '') {
    return;
  }
  // Node取得
  let node ; 
  for (const n of contextG.editor.getNodes())
    if (n.id == nodeid) {
      // console.log('Match!! :'+n.id);
      node = n;
      break;
    }
    // console.log('nodeid='+nodeid+', node:'+node)

  // NodeにDialog入力データをセット
  if (node instanceof systemNode) {
    // System Node
    node.controls.type.value = setVal['type'];
    node.controls.utterance.value = setVal['utterance'];
  }
  else if (node instanceof userNode) {
    // User Node
    node.controls.utterance.value = setVal['utterance'];
    node.controls.type.value = setVal['type'];
    node.controls.conditions.value = setVal['condition'];
    node.controls.actions.value = setVal['action'];
    node.controls.seqnum.value = setVal['priorityNum'];
  }
  // 再レンダリング
  contextG.area.update(`node`, nodeid)
}
