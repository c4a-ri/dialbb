import { ClassicPreset, NodeEditor } from "rete";
import type { GetSchemes } from "rete";
import { systemNode, userNode } from "./nodes";


type Schemes = GetSchemes<
  ClassicPreset.Node,
  ClassicPreset.Connection<ClassicPreset.Node, ClassicPreset.Node>
>;

//-----------------------------------
// Function for Serialize
//-----------------------------------
function serializePort(
  port:
    | ClassicPreset.Input<ClassicPreset.Socket>
    | ClassicPreset.Output<ClassicPreset.Socket>
) {
  return {
    id: port.id,
    label: port.label,
    socket: {
      name: port.socket.name
    }
  };
}

function serializeControl(control: ClassicPreset.Control) {
  if (control instanceof ClassicPreset.InputControl) {
    return {
      __type: "ClassicPreset.InputControl" as const,
      id: control.id,
      readonly: control.readonly,
      type: control.type,
      value: control.value
    };
  }
  return null;
}

function serializeConnection(connection: ClassicPreset.Connection<any, any>) {
  if (connection instanceof ClassicPreset.Connection) {
    return {
      id: connection.id,
      sourceOutput: connection.sourceOutput,
      targetInput: connection.targetInput,
      source: connection.source,
      target: connection.target
    };
  }
  return null;
}


//-----------------------------------
// Check for duplicate types in systemNodes
//-----------------------------------
async function checkStateType(editor: NodeEditor<Schemes>) {
  const typeList: {[name: string]: number } = {}; 

  // Count types
  for (const node of editor.getNodes()) {
    if (node instanceof systemNode) {
      const type = node.controls.type.value ?? 'undefined';
      typeList[type] = (type in typeList) ? typeList[type] + 1 : 1;
    }
  }
  // console.table(typeList)

  // Check for duplicates
  let ngs = '';
  ['prep', 'initial', 'error'].forEach((type) => {
    if (typeList[type] > 1) {
      ngs = (ngs) ? `${ngs},${type}` : type;
    }
  });

  let warn:string = '';
  if (ngs) {
    // ワーニングメッセージを作成
    warn = `type:"${ngs}" is set multiple times.`;
  }
  return warn;
}

//-----------------------------------
// Export editor information to JSON
//-----------------------------------
export async function exportGraph(editor: NodeEditor<Schemes>) {
  const data: any = { nodes: [], connects: [], types: [] };
  const nodes = editor.getNodes();
  const typeList: any = [];

  // Check type
  const warning = await checkStateType(editor);
  if (warning) {
    // Return a warning message
    return {'warning': warning};
  }

  // Save Connections
  const connections = editor.getConnections();
  for (const con of connections) {
    // console.table(con)
    // Get connected pair and Set a nextStatus
    const target = editor.getNode(con.target)
    const source = editor.getNode(con.source)
    // connected from userNode to systemNode
    if (source instanceof userNode && target instanceof systemNode) {
      (source as userNode).controls.nextStatus.value =
        (target as systemNode).controls.status.value
    }

    // Add connection data to json  style. 
    data.connects.push(serializeConnection(con));
  }

  for (const node of nodes) {
    const inputsEntries = Object.entries(node.inputs).map(([key, input]) => {
      return [key, input && serializePort(input)];
    });
    const outputsEntries = Object.entries(node.outputs).map(([key, output]) => {
      return [key, output && serializePort(output)];
    });
    const controlsEntries = Object.entries(node.controls).map(
      ([key, control]) => {
        const cont = control && serializeControl(control)
        return [key, cont];
      }
    );

    // Save a Node
    data.nodes.push({
      id: node.id,
      label: node.label,
      outputs: Object.fromEntries(outputsEntries),
      inputs: Object.fromEntries(inputsEntries),
      controls: Object.fromEntries(controlsEntries)
    });
  }

  // Save list of utterance types
  data.types = Array.from(new Set(typeList))

  return data;
}
