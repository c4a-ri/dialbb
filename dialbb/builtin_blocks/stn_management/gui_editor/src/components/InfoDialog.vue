<!-- Dialog.vue -->
<template>
  <teleport to="body"><transition name="fade">
    <div v-if="isOpen" class="modal">
      <div class="modal" v-on:click.self="isOpen=false">
        <div class="modal-dialog">
          <div class="modal-content">
            <!-- ヘッダー部 -->
            <div class="modal-header">
                <h3 class="modal-title fs-5" id="exampleModalLabel">{{ props.title }}</h3>
            </div>
            
            <!-- body部 -->
            <div class="modal-body">
              <p>{{ props.message }}</p>
            </div>
            
            <!-- フッター部 -->
            <div class="modal-footer">
              <Button type="primary" class="custom-button" size="middle" @click="closeDialog">Close</Button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop show"></div>
    </div>
  </transition></teleport>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Button } from 'ant-design-vue';

// propsの型宣言
interface DialogProps {
  title: string;
  message: string;
}

// 親コンポーネントからの受信データ
const props = defineProps<DialogProps>();

const isOpen = ref(false);
// const title = props.title;
// const message = props.message;

const openDialog = () => {
  isOpen.value = true;
};

const closeDialog = () => {
  isOpen.value = false;
};

defineExpose({
  openDialog,
})

// propsの変更を検知する
watch(props, () => {
  console.log("Message22:"+props.message)
  // openDialog();
});
</script>

<style scoped>
.modal-content {
    padding: 5px;
    width: 280px;
    border-radius: 8px;
    box-shadow: 10px 10px 20px rgba(255, 255, 255, 0.5);
  }

.dialog {
  background-color: white;
  padding: 20px;
  border-radius: 5px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.modal {
    display: block;
  }
  .modal-header h3 {
    margin-top: 0;
    color: #42b983;
  }
  .modal-body {
    margin: 5px 0;
  }
  .modal-footer {
    float: right;
    padding: 5px;
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
