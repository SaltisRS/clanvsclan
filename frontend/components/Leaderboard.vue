<template>
  <div class="bg-dc-accent p-4 rounded-lg shadow-md">
    <h2 class="text-lg font-bold text-white text-center border-b border-dc-bg">
      {{ title }}
    </h2>
    <table class="w-full border-collapse">
      <tbody>
        <tr
          v-for="(entry, index) in displayedData"
          :key="index"
          class="border-b border-dc-bg text-blurple"
        >
          <td class="p-2 font-bold">#{{ index + 1 }}</td>
          <td class="p-2 cursor-pointer hover:brightness-125"
          @click="redirectToWiseOldMan(entry.rsn)"
          >{{ entry.rsn }}</td>
          <td class="p-2 text-right">{{ entry.value }}</td>
          <td class="p-2">
            <img
              v-if="entry.team === 'IF'"
              src="public/ironfoundry.png"
              alt="IF Team Icon"
              class="w-6 h-6"
            />
            <img
              v-if="entry.team === 'IC'"
              src="public/ironclad.png"
              alt="IC Team Icon"
              class="w-6 h-6"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

type LeaderboardEntry = { rsn: string; value: number, team: string };

const redirectToWiseOldMan = (rsn: string) => {
  const url = `https://wiseoldman.net/players/${rsn}`;
  window.open(url, "_blank");
};

const props = defineProps({
  title: String,
  data: { type: Array as () => LeaderboardEntry[], default: () => [] },
  maxRows: { type: Number, default: Infinity },
});

const sortedData = computed(() =>
  [...props.data].sort((a, b) => b.value - a.value)
);

const displayedData = computed(() => sortedData.value.slice(0, props.maxRows));
</script>
