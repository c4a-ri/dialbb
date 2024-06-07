<template>
  <div class="node" :class="{ selected: data.selected }" :style="nodeStyles()" data-testid="node">
    <div class="title" data-testid="title">{{ data.label }}</div>
    <div class="socket-list">
      <!-- Inputs-->
      <div class="input" v-for="[key, input] in inputs()" :key="key + seed" :data-testid="'input-' + key">
        <Ref class="input-socket" :emit="emit"
          :data="{ type: 'socket', side: 'input', key: key, nodeId: data.id, payload: input.socket }"
          data-testid="input-socket" />
        <div class="input-title" v-show="!input.control || !input.showControl" data-testid="input-title">{{ input.label }}
        </div>
        <Ref class="input-control" v-show="input.control && input.showControl" :emit="emit"
          :data="{ type: 'control', payload: input.control }" data-testid="input-control" />
      </div>
      <!-- Outputs-->
      <div class="output" v-for="[key, output] in outputs()" :key="key + seed" :data-testid="'output-' + key">
        <div class="output-title" data-testid="output-title">{{ output.label }}</div>
        <Ref class="output-socket" :emit="emit"
          :data="{ type: 'socket', side: 'output', key: key, nodeId: data.id, payload: output.socket }"
          data-testid="output-socket" />
      </div>
    </div>
    <!-- Controls-->
    <!-- <Ref class="control" v-for="[key, control] in controls()" :key="key + seed" :emit="emit"
      :data="{ type: 'control', payload: control }" :data-testid="'control-' + key" /> -->
    <div class="control" v-for="[key, control] in controls()" :key="key + seed" :data-testid="'control-' + key">
      <div class="control-title" data-testid="control-title">{{ control.label }}</div>
      <Ref v-if="!control.hide" class="control-input" :emit="emit"
        :data="{ type: 'control', payload: control }" data-testid="control-input" />
    </div>
  </div>
</template>


<script setup lang="ts">
  import { systemNode } from ".";;
  import { Ref } from 'rete-vue-plugin'
  
  const props = defineProps<{     // receive from parent
    data: systemNode,
    emit: String,
    seed: String,
  }>();

  const sortByIndex = (entries: any[]) => {
    entries.sort((a, b) => {
      const ai = a[1] && a[1].index || 0
      const bi = b[1] && b[1].index || 0
  
      return ai - bi
    })
    return entries
  }
  
  const nodeStyles = () => {
    return {
      width: Number.isFinite(props.data.width) ? `${props.data.width}px` : '',
      height: Number.isFinite(props.data.height) ? `${props.data.height}px` : ''
    }
  };
  const inputs = () => {
    return sortByIndex(Object.entries(props.data.inputs))
  };
  const controls = () => {
    // console.table(this.data.controls);
    return sortByIndex(Object.entries(props.data.controls))
  };
  const outputs = () => {
    return sortByIndex(Object.entries(props.data.outputs))
  };
</script>
  
<style lang="scss" scoped>
  @use "sass:math";
  @import "./vars";
  
  .node {
    background: rgba(243, 168, 106, 0.637);
    border: 2px solid grey;
    border-radius: 10px;
    cursor: pointer;
    box-sizing: border-box;
    width: $node-width;
    height: auto;
    padding-bottom: 6px;
    position: relative;
    user-select: none;
  
    &:hover {
      background: #ffd92c;
    }
  
    &.selected {
      border-color: red;
    }
  
    .title {
      color: black;
      font-family: sans-serif;
      font-size: 20px;
      padding: 8px;
    }
  
    .socket-list {
      display:flex;
      justify-content:space-between;
    }
  
    .output-socket {
      margin-right: -1.2em;
      display: inline-block;
    }
  
    .input-socket {
      margin-left: -1.2em;
      display: inline-block;
    }
  
    .input-title,
    .output-title {
      vertical-align: middle;
      color: white;
      display: inline-block;
      font-family: sans-serif;
      font-size: 14px;
      margin: $socket-margin;
      line-height: $socket-size;
    }
  
    .input-control {
      z-index: 1;
      width: calc(100% - #{$socket-size + 2*$socket-margin});
      vertical-align: middle;
      display: inline-block;
    }
  
    .control {
      padding: $socket-margin math.div($socket-size, 2) + $socket-margin;
    }

    .control-input {
      height: 30px;
    }

    .control-title {
      color: black;
    }
  }
</style>
