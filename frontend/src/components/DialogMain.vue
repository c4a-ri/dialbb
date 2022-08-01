<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import SystemUtterance from './SystemUtterance.vue'
import UserUtterance from './UserUtterance.vue'
import axios from 'axios'

interface Utterance {
  component: String,
  utterance: String
}

const utterances = reactive<Utterance[]>([])
const input_text = ref<String>("");
let isStarted = false;
let session_id = ""
const user_id = ref<string>("user")
const getComponent = (utterance: Utterance) => {
  if (utterance.component == "SystemUtterance") return SystemUtterance;
  else return UserUtterance;
}

const keydown = (event: KeyboardEvent) => {
  if(event.key !=="Enter" ) return 
  textinput()
}
const textinput = async () => {
  const user_utterance = input_text.value
  if (user_utterance.length == 0) return
  console.log(`user utterance =${user_utterance}`)
  utterances.push({
    component: "UserUtterance",
    utterance: user_utterance,
  });
  const res = await axios.post('/dialogue', { user_id: user_id.value, session_id: session_id, user_utterance: user_utterance })
  console.log(`system utterance = ${res.data.system_utterance}`)
  utterances.push({
    component: 'SystemUtterance',
    utterance: res.data.system_utterance
  })
  input_text.value = ""
  scrollEnd();
}
const start = async () => {
  try {
    const res = await axios.post('/init', { user_id: user_id.value, })
    console.log(`session_id = ${res.data.session_id}`)
    session_id = res.data.session_id
    console.log(`system utterance = ${res.data.system_utterance}`)
    utterances.push({
      component: 'SystemUtterance',
      utterance: res.data.system_utterance
    })
    isStarted = true;
  } catch (e) {
    if (e instanceof Error) {
      utterances.push({
        component: "SystemUtterance",
        utterance: `System Error - ${e.message}`
      })

    } else {

    }
  }

}
const scrollEnd = () => {

  nextTick(() => {
    const scrollElement = document.getElementById('scroll');
    const bottom = scrollElement?.scrollHeight!! - scrollElement?.clientHeight!!
    console.log(`bottom = ${bottom}`)
    scrollElement?.scroll(0, bottom)
  })

}
</script>
<template>
  <div class="container d-flex flex-column">
    <header>
      <div class="row">
        <div class="col-auto">
          <h1 class="h1">DialBB Application Frontend</h1>
        </div>
        <div class="col-auto">
          <input type="text" class="form-control" v-model="user_id" placeholder="user id" />
        </div>
        <div class="col-auto">
          <button class="btn btn-primary" v-bind:disabled="isStarted" @click="start()">start dialouge</button>
        </div>
      </div>
    </header>
    <article>
      <div class="scroll" id="scroll">
        <div class="row" v-for="utterance in utterances">
          <component :is="getComponent(utterance)" :utterance="utterance.utterance" />
        </div>
      </div>
    </article>
    <footer>
      <div class="row">
        <div class="col-auto">
          <input type="text" class="form-control" v-model="input_text" @keydown.enter="keydown" placeholder="input utterance" />
        </div>
        <div class="col-auto">
          <button
            class="btn btn-primary"
            v-bind:disabled="(input_text.length == 0) || !isStarted"
            @click="textinput()"
          >send</button>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
a {
  color: #42b983;
}

label {
  margin: 0 0.5em;
  font-weight: bold;
}
header {
  margin: 10px;
}
.container {
  overflow-y: auto;
  overflow-x: visible;
  min-height: 100vh;
  height: 100vh;
}
.scroll {
  overflow-y: auto;
  overflow-x: hidden;
  height: 100%;
}
article {
  overflow-y: visible;
  overflow-x: hidden;
  flex-grow: 1;
}
footer {
  margin: 10px;
}
code {
  background-color: #eee;
  padding: 2px 4px;
  border-radius: 4px;
  color: #304455;
}
</style>
