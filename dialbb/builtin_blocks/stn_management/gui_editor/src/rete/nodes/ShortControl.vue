<template>
    <input :type="data.type"
      :value="data.value"
      :readonly="data.readonly"
      @input="change"
      @pointerdown.stop="">
    </input>
</template>
  
<script setup lang="ts">
  import { ClassicPreset as Classic } from "rete";
  
  const props = defineProps<{     // receive from parent
    data: Classic.InputControl<"text"|"number">,
  }>();

  const change = (e:any) => {
    const val = props.data.type === 'number'
      ? +e.target.value
      : e.target.value

    props.data.setValue(val)
  }
</script>
  
<style lang="scss" scoped>
  @use "sass:math";
  @import "./vars";
  
input {
  width: 60px;
  height: 26px;
  border-radius: 14px;
  background-color: white;
  padding: 2px 6px;
  border: 1px solid #999;
  font-size: 110%;
  box-sizing: border-box;
}
</style>
  