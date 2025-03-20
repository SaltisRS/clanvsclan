<template>
  <main
    class="flex justify-center items-center p-20 gap-8 select-none"
  >
    <div v-if="loading">
      <Loading />
    </div>

    <div>
      <div>
        <Navbar />
        <Refresh class="z-50" />
      </div>
    </div>
    <div class="flex flex-col sm:flex-row flex-wrap gap-12 justify-center">
  <Leaderboard v-for="board in jsonData" :key="board.title" :title="board.title" :data="board.data"/>
    </div>
  </main>
</template>

<script setup lang="ts">
import { Navbar, Loading, Refresh, Leaderboard} from "#components";
import jsonData from "@/leaderboards.json"
const loading = ref<boolean>(false);
</script>
