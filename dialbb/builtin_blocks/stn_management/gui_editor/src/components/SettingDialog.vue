<script setup lang="ts">
import { ref, onBeforeUpdate } from 'vue'
import { saveNodeValue } from '../rete/editor';

const open = ref(false)

// 親コンポーネントからのデータ
const props = defineProps({
  nodeId: String,
  nodeKind: String,
  status: String,
  statustype: String,
  systemutter: String,
  userutter: String,
  uttertype: String,
  condition: String,
  action: String,
  typeItems: Array,
})

// textereaにバインドする変数
const inputSystem = ref()
const inputUser = ref()
const inputType = ref()
const inputStatusType = ref()
const inputStatus = ref()
const inputCondition = ref()
const inputAction = ref()
const selectItems = ref()
const newOption = ref('');

// DOMを更新する前に実行
onBeforeUpdate(() => {
  // 親コンポーネントからのデータを載せ替え（propsはReadOnlyのため）
  inputStatus.value = props.status;
  inputStatusType.value = props.statustype;
  inputSystem.value = props.systemutter;
  inputUser.value = props.userutter;
  inputType.value = props.uttertype;
  inputCondition.value = props.condition;
  inputAction.value = props.action;
  selectItems.value = props.typeItems;
});

// 関数の実装（公開はdefineExposeで）
// モーダルウィンドウ表示 (コンテキストメニュー：[Setting])
const doOpen = () => {
  console.table(props);
  console.log(`Called doOpen() Recieved  id=${props.nodeId} kind=${props.nodeKind}.`);
  open.value = true;
};
// モーダルウィンドウ閉じる[X]/[Close]
const doClose = () => {
  open.value = false;
};
// データセーブ[Save]
const doSave = () => {
  //console.log("id="+props.nodeId);
  let setValues = {};
  if (props.nodeKind == 'systemNode') {
    setValues = {'type': inputStatusType.value,
      'status': inputStatus.value, 'utterance': inputSystem.value};
  }
  else if (props.nodeKind == 'userNode') {
    setValues = {'utterance': inputUser.value, 'type': inputType.value,
      'condition': inputCondition.value, 'action': inputAction.value};
  }
  // Nodeに反映するfunction(->editor.ts)
  saveNodeValue(props.nodeId, setValues);
  open.value = false;
};

// 発話タイプを動的に追加する
const addOption = () => {
  const newop = newOption.value.trim()
  if (!selectItems.value.includes(newop)) {
    doClose();
    selectItems.value.push(newOption.value);
    newOption.value = '';
    doOpen();
  }
  console.log('selectItems:'+selectItems.value)
};

// defineExpose を使用してコンポーネント内に定義されたメソッドを親コンポーネントから参照できる様にしています。
defineExpose({
  doOpen,
  doClose,
  doSave,
})
</script>

<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="open" class="modal">
        <div class="modal" v-on:click.self="open=false">
          <div class="modal-dialog">
              <div class="modal-content">
              <!-- ヘッダー部 -->
              <div class="modal-header">
                  <h1 class="modal-title fs-5" id="exampleModalLabel">シナリオの設定</h1>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" @click="doClose"></button>
              </div>
              
              <!-- ダイアログ入力項目 -->
              <div class="modal-body">
                <form>
                  <div v-if="nodeKind == 'systemNode'">
                    <div class="dropdown">
                      <label for="status-type" class="col-form-label">type:</label>
                      <select class="form-select" aria-label="Default select example" v-model="inputStatusType">
                          <option value='' disabled selected style='display:none;'>タイプを選択</option>
                          <option v-for="state in selectItems">{{ state }}</option>
                      </select>
                    </div>
                    <div class="mb-3">
                        <label for="status-name" class="col-form-label">name:</label>
                        <textarea class="form-control" id="status-name" v-model="inputStatus"
                                    title="状態名を入力してください（省略可）"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="system-utter" class="col-form-label">システム発話:</label>
                        <textarea class="form-control" id="system-utter" v-model="inputSystem"
                                    title="システム発話を入力してください。"></textarea>
                    </div>
                  </div>
                  <div v-else-if="nodeKind == 'userNode'">
                    <div class="mb-3">
                        <label for="user-utter" class="col-form-label">ユーザ発話:</label>
                        <textarea class="form-control" id="user-utter" v-model="inputUser"
                                    title="ユーザ発話を入力してください。"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="utter-type" class="col-form-label">発話タイプ:</label>
                        <textarea class="form-control" id="utter-type" v-model="inputType"
                                    title="発話タイプを入力してください。"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="condition" class="col-form-label">条件:</label>
                        <textarea class="form-control" id="condition" v-model="inputCondition"
                                    title="条件を入力してください。"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="action" class="col-form-label">アクション:</label>
                        <textarea class="form-control" id="user-utter" v-model="inputAction"
                                    title="アクションを入力してください。"></textarea>
                    </div>
                  </div>
                </form>
              </div>
              <!-- フッター部 -->
              <div class="modal-footer">
                  <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" @click="doClose">Close</button>
                  <button type="button" class="btn btn-primary" @click="doSave">Save</button>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-backdrop show"></div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-content {
  padding: 10px;
  border-radius: 8px;
  box-shadow: 10px 10px 20px rgba(255, 255, 255, 0.5);
}
.modal-header h1 {
margin-top: 0;
color: #42b983;
}

/* 表示/非表示はvueで制御するので最初から表示状態にする */
.modal {
  display: block;
}
/* vueのtransitionを使わないなら不要 */
.fade-enter-active, .fade-leave-active {
  transition: opacity .15s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
</style>