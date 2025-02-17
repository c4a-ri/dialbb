<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { createEditor } from './rete/editor';
import SettingDialog from './components/SettingDialog.vue';
import AddNewType from './components/AddNewType.vue';
import InfoDialog from './components/InfoDialog.vue';
import { Space, Button } from 'ant-design-vue';
import "./rete/styles.css";


const rete = ref<HTMLElement>()
const editor = ref()
const state = reactive({
  nodeId: ref(''),
  nodeKind: ref(''),
  statustype: ref(''),
  systemutter: ref(''),
  userutter: ref(''),
  uttertype: ref(''),
  condition: ref(''),
  action: ref(''),
  priorityNum: ref(0)
})

const jsonDataPath = ref('static/data/init.json')
const typeItems = ref(["example-1", "example-2", "example-3", "othe"])
const showModal = ref(false)

// データセーブ[Save]
const doExport =  async () => {
  console.log("Click Button doExport()");
  const result = await editor.value.saveModule(import.meta.env.DEV, 'save.json');
  if ('warning' in result) {
    openInformationDialog(result['warning']);
  }
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

// Information Dialog表示
const childRef3 = ref()
const infoDlgTitle = ref('Warning');
const infoDlgMessage = ref('');

const openInformationDialog = (msg: string) => {
  infoDlgMessage.value = msg;
  // 子コンポーネント起動
  childRef3.value.openDialog();
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
      <Space class="container" size="small">
        <h3>DialBB GUI Scenario Editor</h3>
        <Button type="primary" class="custom-button" size="middle" @click="doExport()">Save</Button>
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
    <input type="hidden" id="userwordsInput" v-model="state.userutter"/>
    <input type="hidden" id="uttertypeInput" v-model="state.uttertype"/>
    <input type="hidden" id="conditionInput" v-model="state.condition"/>
    <input type="hidden" id="actionInput" v-model="state.action"/>
    <input type="hidden" id="priorityNumInput" v-model.number="state.priorityNum"/>

    <!-- setting dialog -->
    <div id="dialoginfo" >
      <SettingDialog ref="childRef" v-bind="state" :typeItems="typeItems"/>
    </div>
    <!-- AddNewType dialog -->
    <div id="dialoginfo2" >
      <AddNewType ref="childRef2" :title="'発話タイプ追加'" @addType="addTypeConfirm" />
    </div>
    <!-- Information dialog -->
    <div id="dialoginfo3" >
      <InfoDialog ref="childRef3" :title="infoDlgTitle" :message="infoDlgMessage" />
    </div>

    <!-- node editor area -->
    <main class="rete" ref="rete"></main>
  </div>
</template>

<style scoped>
  .container {
    display: flex;
    justify-content: space-between; /* 要素をコンテナの両端に配置 */
    align-items: center;
  }
  
  h3 {
    margin: 0;
  }
</style>
