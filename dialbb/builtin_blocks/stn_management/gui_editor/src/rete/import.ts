import { Connection } from "./editor";
import type { Context } from "./editor";
import {
  systemNode,
  userNode
} from "./nodes";

export async function createNode(
  { editor, area, engine, modules, process }: Context,
  name: string,
  data: any
) {
  // console.log('name='+name)
  // console.table(data)
  if (name === "systemNode") {
    let node: any;
    if ( data ) {
      const ctrl = data.controls;
      node = new systemNode(process,
        (node) => area.update("control", node.id),
        ctrl.type.value, ctrl.status.value, ctrl.utterance.value
      );
    } else {
      node = new systemNode(process,
        (node) => area.update("control", node.id));
    }
    return node;
  }
  else if (name === "userNode") {
    let node: any;
    if ( data ) {
      const ctrl = data.controls;
      node = new userNode(process,
        (node) => area.update("control", node.id),
        ctrl.utterance.value, ctrl.type.value,
        ctrl.conditions.value, ctrl.actions.value,
        ctrl.seqnum.value, ctrl.nextStatus.value
      );
    } else {
      node = new userNode(process,
        (node) => area.update("control", node.id));
    }
    return node;
  }
  throw new Error("Unsupported node");
}

// ImportデータからNodeを生成する
export async function importEditor(context: Context, data: any) {
  const { nodes, connects } = data;

  // Nodeの生成
  for (const n of nodes) {
    const node = await createNode(context, n.label, n);
    node.id = n.id;
    await context.editor.addNode(node);
  }
  // Connectionの接続
  for (const c of connects) {
    const source = context.editor.getNode(c.source);
    const target = context.editor.getNode(c.target);

    if (
      source &&
      target &&
      (source.outputs as any)[c.sourceOutput] &&
      (target.inputs as any)[c.targetInput]
    ) {
      const conn = new Connection(
        source,
        c.sourceOutput as never,
        target,
        c.targetInput as never
      );

      await context.editor.addConnection(conn);
    }
  }
}

// NodeデータをExportする
// export function exportEditor(context: Context) {
//   const nodes = [];
//   const connections = [];

//   for (const n of context.editor.getNodes()) {
//     nodes.push({
//       id: n.id,
//       name: n.label,
//       data: n.serialize()
//     });
//   }
//   for (const c of context.editor.getConnections()) {
//     connections.push({
//       source: c.source,
//       sourceOutput: c.sourceOutput,
//       target: c.target,
//       targetInput: c.targetInput
//     });
//   }

//   return {
//     nodes,
//     connections
//   };
// }
