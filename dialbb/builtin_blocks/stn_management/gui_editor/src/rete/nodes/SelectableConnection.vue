<template>
  <!-- <svg data-testid="connection" :class="{ 'svg1': !selected, 'svg2': selected }"> -->
  <svg data-testid="connection" class="svg1">
    <path :d="path"></path>
  </svg>
</template>
  
<script setup lang="ts">
  import { ref, defineComponent } from 'vue';

  const props = defineProps<{
    path: any,
    // selected: boolean,
  }>();
  const selected = ref()

  // export default defineComponent({
  //     props: ['data', 'start', 'end', 'path']
  // }
  const setSelector = () => {
    selected.value = true
    console.log('setSelector:'+selected.value)
  };

  // defineExpose を使用してコンポーネント内に定義されたメソッドを親コンポーネントから参照できる様にしています。
  defineExpose({
    setSelector,
  })

</script>
  
<style lang="scss" scoped>
  .svg1 {
    overflow: visible !important;
    position: absolute;
    pointer-events: none;
    width: 9999px;
    height: 9999px;
    path {
      fill: none;
      stroke-width: 5px;
      stroke: black;
      pointer-events: auto;
      &:hover {
        stroke: rgb(255, 166, 0);
      }
      &.selected {
      stroke: red;
      }
    }
  }
  .svg2 {
    overflow: visible !important;
    position: absolute;
    pointer-events: none;
    width: 9999px;
    height: 9999px;
    path {
      fill: none;
      stroke-width: 5px;
      stroke: yellow;
      pointer-events: auto;
      &:hover {
        stroke: blue;
      }
    }
  }
</style>
