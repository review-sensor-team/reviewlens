<template>
  <ChatBot />
</template>

<script setup>
import ChatBot from './components/ChatBot.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 
    'Helvetica Neue', Arial, sans-serif;
  background: #f5f5f5;
}

#app {
  height: 100vh;
}
</style>
