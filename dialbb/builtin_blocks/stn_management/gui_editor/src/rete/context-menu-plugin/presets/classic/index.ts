import { NodeEditor } from 'rete'
import { BaseAreaPlugin } from 'rete-area-plugin'

import type { Item, Items } from '../../types'
import { createItem } from './factory'
import type { BSchemes, ItemDefinition } from './types'
import { getCurrentInstance } from 'vue';
import {
  systemNode,
  userNode
} from "../../../nodes";
import { Connection } from "../../../editor";

/**
 * Classic context menu preset.
 * Configures nodes/actions items for root and Delete/Clone items for nodes
 * @param nodes List of items
 * @example Presets.classic.setup([
  ["Math", [
    ["Number", () => new NumberNode()],
  ]]
])
 */
export default {
  setup() {
    console.log("@@@> "+getCurrentInstance());
  },
};
export function setup<Schemes extends BSchemes>(nodes: ItemDefinition<Schemes>[]) {
  return <Items<Schemes>>(function (context, plugin) {
    const area = plugin.parentScope<BaseAreaPlugin<Schemes, any>>(BaseAreaPlugin)
    const editor = area.parentScope<NodeEditor<Schemes>>(NodeEditor)

    if (context === 'root') {
      return {
        searchBar: true,
        list: nodes.map((item, i) => createItem(item, i, { editor, area }))
      }
    }

    const deleteItem: Item = {
      label: 'Delete',
      key: 'delete',
      async handler() {
        if (context instanceof systemNode ||
            context instanceof userNode ) {
          const nodeId = context.id
          const connections = editor.getConnections().filter(c => {
            return c.source === nodeId || c.target === nodeId
          })

          for (const connection of connections) {
            await editor.removeConnection(connection.id)
          }
          await editor.removeNode(nodeId)
        }
        else if (context instanceof Connection) {
          console.log("### context.id="+context.id)
          await editor.removeConnection(context.id)
        }

      }
    }

    const clone = context.clone
    const cloneItem: undefined | Item = clone && {
      label: 'Clone',
      key: 'clone',
      async handler() {
        const node = clone()

        await editor.addNode(node)

        area.translate(node.id, area.area.pointer)
      }
    }

    // Dialog Pop-up (added ohtaki)
    const dialogItem: Item = {
      label: 'Edit',
      key: 'dialog',
      async handler() {
        const nodeId = context.id
        console.log("##>nodeId:"+context.id+" Type:"+(typeof context))
        console.table(context)
        console.log('------------');

        // ノードデータをダイアログに反映
        if (context instanceof systemNode) {
          // システムノード
          const nodeData = context as systemNode
          const event = new Event('input');
          // 発話
          let domInput = document.getElementById('syswordsInput') as HTMLInputElement;
          domInput.value = nodeData.controls.utterance.value as string;
          await (domInput as HTMLInputElement).dispatchEvent(event);
          // 状態Type
          domInput = document.getElementById('statustypeIn') as HTMLInputElement;
          console.log("##>statustype:"+nodeData.controls.type.value)
          domInput.value = nodeData.controls.type.value as string;
          console.log("##>domInput.value:"+domInput.value)
          await (domInput as HTMLInputElement).dispatchEvent(event);
  
          // カレントnode-IDとノード種別を設定
          const saveid = document.getElementById('currentNodeId') as HTMLInputElement;
          saveid.value = nodeId;
          await (saveid as HTMLInputElement).dispatchEvent(event);
          const savekind = document.getElementById('nodeKind') as HTMLInputElement;
          savekind.value = 'systemNode';
          await (savekind as HTMLInputElement).dispatchEvent(event);
  
          // ノード設定ダイアログの表示
          await document.getElementById('openModalBtn')?.click();
        }
        else if (context instanceof userNode) {
          // ユーザノード
          const nodeData = context as userNode
          const event = new Event('input');
          // 優先番号
          const domInputNum = document.getElementById('priorityNumInput') as HTMLInputElement;
          domInputNum.value = nodeData.controls.seqnum.value?.toString() as string;
          await (domInputNum as HTMLInputElement).dispatchEvent(event);
          
          // 発話
          let domInput = document.getElementById('userwordsInput') as HTMLInputElement;
          domInput.value = nodeData.controls.utterance.value as string;
          await (domInput as HTMLInputElement).dispatchEvent(event);
          // 発話Type
          domInput = document.getElementById('uttertypeInput') as HTMLInputElement;
          domInput.value = nodeData.controls.type.value as string;
          await (domInput as HTMLInputElement).dispatchEvent(event);
          // 条件
          domInput = document.getElementById('conditionInput') as HTMLInputElement;
          domInput.value = nodeData.controls.conditions.value as string;
          await (domInput as HTMLInputElement).dispatchEvent(event);
          // アクション
          domInput = document.getElementById('actionInput') as HTMLInputElement;
          domInput.value = nodeData.controls.actions.value as string;
          await (domInput as HTMLInputElement).dispatchEvent(event);
  
          // カレントnode-IDとノード種別を設定
          const saveid = document.getElementById('currentNodeId') as HTMLInputElement;
          saveid.value = nodeId;
          await (saveid as HTMLInputElement).dispatchEvent(event);
          const savekind = document.getElementById('nodeKind') as HTMLInputElement;
          savekind.value = 'userNode';
          await (savekind as HTMLInputElement).dispatchEvent(event);
  
          // ノード設定ダイアログの表示
          await document.getElementById('openModalBtn')?.click();
        }
      }
    }
    
    if (context instanceof Connection) {
      // Connectionは[Delete]のみ
      return {
        searchBar: false,
        list: [
          deleteItem,
        ]
      }
    }
    else {
      // Nodeは[Delete, Edit]
      return {
        searchBar: false,
        list: [
          deleteItem,
          dialogItem,
          ...(cloneItem ? [cloneItem] : [])
        ]
      }
    }
  })
}
