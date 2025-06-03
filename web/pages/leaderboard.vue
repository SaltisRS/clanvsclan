<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Navbar, Loading, Refresh, Leaderboard } from "#components";

interface RowData {
  index: number;
  rsn: string;
  value: number;
  profile_link: string; // Player profile URL should become clickable redirect on RSN
  icon_link: string;
}

interface LeaderboardEntry {
  title: string;
  metric_page?: string; // Wiseoldman URL should become a clickable Title redirect
  data: RowData[];
}

interface ApiResponse {
  Data: LeaderboardEntry[];
}

const loading = ref<boolean>(false);
const jsonData = ref<LeaderboardEntry[]>([]);

const fetchLeaderboardData = async () => {
  loading.value = true;
  try {
    const response = await fetch("https://frenzy.ironfoundry.cc/leaderboards");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const apiResponse: ApiResponse = await response.json();
    jsonData.value = apiResponse.Data;
  } catch (error) {
    console.error("Failed to fetch leaderboard data:", error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchLeaderboardData();
});
</script>

<template>
  <main
    class="flex justify-center items-start p-8 md:p-10 lg:p-12 select-none min-h-screen"
  >
    <div v-if="loading" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50">
      This may take a moment on data flush...
      <Loading />
    </div>

    <div class="absolute top-0 right-0 m-4 z-50">
      <Navbar />
      <Refresh class="mt-2" />
    </div>

    <!-- This div wraps all the individual leaderboard cards -->
    <div
      class="flex flex-col sm:flex-row flex-wrap gap-4 md:gap-6 justify-center w-full max-w-7xl pt-20"
      v-if="!loading && jsonData.length > 0"
    >
      <!-- Each 'board' is a LeaderboardEntry from your fetched data -->
      <Leaderboard
        v-for="board in jsonData"
        :key="board.title"
        :title="board.title"
        :data="board.data"
        :metric-page="board.metric_page"
      />
    </div>

    <div
      v-else-if="!loading && jsonData.length === 0"
      class="text-white text-xl"
    >
      No leaderboard data available.
    </div>
  </main>
</template>