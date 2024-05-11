<template>
  <teleport to="body"><transition name="fade">
    <div v-if="open" class="modal">
      <div class="modal" v-on:click.self="open=false">
      <div class="modal-dialog">
      <div class="modal-content">
        <!-- ヘッダー部 -->
        <div class="modal-header">
            <h2 class="modal-title fs-5" id="exampleModalLabel">{{ props.title }}</h2>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close" @click="doClose">
            </button>
        </div>
        
        <div class="modal-body">
        <!-- 入力エリア -->
        <input v-model="inputValue" @keyup.enter="handleEnter" />

        <!-- フッター部 -->
        <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="doClose">Cancel</button>
            <button type="button" class="btn btn-primary" data-bs-dismiss="modal" @click="handleConfirm(inputValue)">
                OK</button>
        </div>
        </div>
      </div>
      </div>
      </div>
      <div class="modal-backdrop show"></div>
    </div>
  </transition></teleport>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  
  const props = defineProps(['title']);     // receive from parent
  const emits = defineEmits(['addType'])    // return to parent
  
  const inputValue = ref<string>('');
  const open = ref(false)

  // モーダルウィンドウ表示 (コンテキストメニュー：[Setting])
  const doOpen = () => {
    inputValue.value = '';
    open.value = true;
  };
  const handleEnter = () => {
    open.value = false;
    // 親コンポーネントに渡す
    emits('addType', inputValue.value)
  };
  const handleConfirm = (value?: string) => {
    open.value = false;
    // 親コンポーネントに渡す
    emits('addType', value)
  };
  // モーダルウィンドウ閉じる[X]/[Close]
  const doClose = () => {
    open.value = false;
  };

  defineExpose({
    doOpen,
  })
</script>
  
<style scoped>
  .modal-content {
    padding: 5px;
    width: 280px;
    border-radius: 8px;
    box-shadow: 10px 10px 20px rgba(255, 255, 255, 0.5);
  }
  .modal {
    display: block;
  }
  .modal-header h2 {
  margin-top: 0;
  color: #42b983;
  }
  .modal-body {
    margin: 5px 0;
  }
  .modal-footer {
    float: right;
  }
  /* vue for transition */
  .fade-enter-active, .fade-leave-active {
    transition: opacity .15s;
    /* transition: opacity 0.3s ease; */
  }
  .fade-enter, .fade-leave-to {
    opacity: 0;
  }
</style>
  