<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { createEditor } from './rete/editor';
import SettingDialog from './components/SettingDialog.vue';
import AddNewType from './components/AddNewType.vue';
import { Space, Button } from 'ant-design-vue';
import "./rete/styles.css";


const rete = ref<HTMLElement>()
const editor = ref()
const state = reactive({
  nodeId: ref(''),
  nodeKind: ref(''),
  status: ref(''),
  statustype: ref(''),
  systemutter: ref(''),
  userutter: ref(''),
  uttertype: ref(''),
  condition: ref(''),
  action: ref(''),
})

const jsonDataPath = ref('static/data/init.json')
const typeItems = ref(["example-1", "example-2", "example-3", "othe"])
const showModal = ref(false)

// Editor初期化[New]
const doReset = () => {
  console.log("Click Button doReset()");
  editor.value.resetEditor();
}
// データロード[Import]
const doImport = async (event: any) => {
  console.log("Click Button doImport()");
  const file = event.target.files[0];
  if (file.type !== 'application/json') {
    console.error('File type not JSON, :'+file.name);
    return;
  }
  const reader = new FileReader();
  // 読み込み完了処理
  reader.onload = async (e) => {
    if (reader.result != null && typeof reader.result === "string") {
      const data = JSON.parse(reader.result);
      // 読み込みJSONデータで再描画, 発話タイプ一覧をプルダウンリストに設定
      typeItems.value = await editor.value.openModule(data);
    }
  };
  // File read
  reader.readAsText(file);
}
// データセーブ[Export]
const doExport =  () => {
  console.log("Click Button doExport()");
  editor.value.saveModule(import.meta.env.DEV, 'save.json');
}
// Setting Dialog表示
const childRef = ref()
const onChildMethodClick = () => {
  childRef.value.doOpen();
}
// 発話タイプ追加Dialog表示
const childRef2 = ref()
const addTypeValue = ref('');
const addTypeDialog = () => {
  // 子コンポーネント起動
  childRef2.value.doOpen();
};
const addTypeConfirm = (value: string) => {
  console.log('Input Value:', value);
  typeItems.value.push(value);
};

onMounted(async () => {
  // Rete Viewport 表示
  if (rete.value) {
    editor.value = await createEditor(rete.value);

    // 初期データを読み込む
    let data = {};
    try {
      const response = await fetch(jsonDataPath.value); // 外部ファイルの取得
      if (!response.ok) {
        throw new Error('Failed to fetch file. '+jsonDataPath.value);
      }
      data = await response.json(); // JSONデータに設定
    } catch (error) {
      console.log('Failed to fetch file. '+jsonDataPath.value);
      console.error(error);
    }
    // Nodeを生成する
    const st_types = await editor.value.openModule(data);
    // 取得した発話タイプ一覧をプルダウンリストに初期設定する
    console.log("Types:"+st_types);
    typeItems.value = st_types;
  }
})

</script>

<template>
  <head>
    <title>Dialbb editor</title>
    <link rel="stylesheet" href="https://ajax.aspnetcdn.com/ajax/jquery.mobile/1.4.5/jquery.mobile-1.4.5.css">
  </head>

  <div id="app">
    <header>
      <Space size="small">
        <h3>DialBB GUIシナリオエディタ　　</h3>
        <Button class="custom-button" size="small" @click="doReset">Clear</Button>
        
        <Button class="custom-button" size="small" @click="doExport()">Save</Button>
        <label for="file" class="filelabel">Load</label>
        <input ref="file" class="fileinput" id="file" type="file" name="fileinput" @change="doImport" />
      </Space>
      <Button id="openModalBtn" class="hidden" size="small" @click="onChildMethodClick">
      Open Modal</Button>
      <!-- <Button class="custom-button" size="small" @click="addTypeDialog">Add New Type</Button> -->
    </header>

    <!-- Nodeの設定値共有エリア(hidden) -->
    <input type="hidden" id="currentNodeId" v-model="state.nodeId"/>
    <input type="hidden" id="nodeKind" v-model="state.nodeKind"/>
    <input type="hidden" id="syswordsInput" v-model="state.systemutter"/>
    <input type="hidden" id="statustypeIn" v-model="state.statustype"/>
    <input type="hidden" id="statusInput" v-model="state.status"/>
    <input type="hidden" id="userwordsInput" v-model="state.userutter"/>
    <input type="hidden" id="uttertypeInput" v-model="state.uttertype"/>
    <input type="hidden" id="conditionInput" v-model="state.condition"/>
    <input type="hidden" id="actionInput" v-model="state.action"/>

    <!-- setting dialog -->
    <div id="dialoginfo" >
      <SettingDialog ref="childRef" v-bind="state" :typeItems="typeItems"/>
    </div>
    <!-- AddNewType dialog -->
    <div id="dialoginfo2" >
      <AddNewType ref="childRef2" :title="'発話タイプ追加'" @addType="addTypeConfirm" />
    </div>

    <!-- node editor area -->
    <main class="rete" ref="rete"></main>
  </div>
</template>
