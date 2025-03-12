<script setup lang="ts">
import {onMounted} from "vue"
import { Loading, Navbar, Refresh, PointBox } from "#components"


const activeData = ref<any>()
const team_uris = ["ironfoundry", "ironclad"]
const selectedTier = ref<any>("Easy")
const selectedTable = ref<string>(team_uris[0])
const loading = ref<boolean>(false)


const fetchTable = async (table: string) => {
  console.log("Fetching table data...")
  loading.value = true

  const minLoadingTime = 200
  const startTime = Date.now()

  try {
    const response = await fetch(`http://frenzy.ironfoundry.cc:8000/${table}`);
    if (!response.ok) throw new Error("Failed to fetch data");

    const _data = await response.json();
    activeData.value = _data[0];
    selectedTier.value = Object.keys(activeData.value.tiers)[0]; // Default to first tier
  } catch (error) {
    console.error("Error fetching table data:", error);
  } finally {
    const elapsedTime = Date.now() - startTime;
    const remainingTime = minLoadingTime - elapsedTime;
    setTimeout(() => {
        loading.value = false
    }, remainingTime * 1000)
  }
}


onMounted(() => fetchTable(team_uris[0]))


const showDetails = (event: MouseEvent) => {
    const target = event.currentTarget as HTMLElement
    const table = target.querySelector("td.details-cell table")

    if (table) {
        table.classList.toggle("hidden")
    }
};
</script>

<template>
  <main class="flex flex-col justify-center items-center p-20 gap-10">

    <div v-if="loading">
        <Loading/>
    </div>

    <div vif="!loading">
        <Navbar/>
    </div>

    <!-- Image Buttons -->
    <div v-if="!loading && activeData" class="flex gap-40">
      <img v-for="table in team_uris" :key="table" :src="'/${table}.png'"
        @click="() => { selectedTable = table; fetchTable(table); }"
        class="size-40 rounded-full border-4 cursor-pointer transition-all duration-200"
        :class="selectedTable === table ? 'border-white shadow-lg scale-110' : 'border-black opacity-70 hover:opacity-100'" />
    </div>


    <!-- Tier Buttons -->
    <div class="flex gap-4">
      <button
        v-for="(_, key) in activeData.tiers"
        :key="key"
        @click="selectedTier = key"
        :class="selectedTier === key ? 'text-yellow-400' : 'text-white'"
        class="bg-osrs-dark-gray px-4 py-2 rounded-lg border border-black"
      >
        {{ key }}
      </button>
    </div>

    <table class="bg-osrs-dark-gray w-4/5 rounded-3xl">
      <thead>
        <tr>
          <th class="p-2 w-1/5">Name</th>
          <th class="p-2 w-4/5">Details</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(source, key) in activeData.tiers[selectedTier].sources"
          :key="key"
          class="border-t border-black hover:bg-gray-800 cursor-pointer"
          @click="showDetails"
        >
          <td class="px-4">{{ source.name }}</td>
          <td class="details-cell">
            <table class="hidden">
              <thead>
                <tr>
                  <th class="w-1/5 p-1">Name</th>
                  <th class="w-1/5 p-1">Points</th>
                  <th class="w-1/5 p-1">Duplicate points</th>
                  <th class="w-1/5 p-1">Obtained</th>
                  <th class="w-1/5 p-1">Duplicate obtained</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, key) in source.items" :key="key">
                  <td class="p-1">{{ item.name }}</td>
                  <td class="text-center p-1">
                    {{ item.points }}
                  </td>
                  <td class="text-center p-1">
                    {{ item.duplicate_points }}
                  </td>
                  <td class="text-center p-1">
                    <Icon
                      v-if="item.obtained"
                      name="nrk:media-media-complete"
                    />
                    <Icon
                      v-else="item.obtained"
                      name="nrk:media-media-incomplete"
                    />
                  </td>
                  <td class="text-center p-1">
                    <Icon
                      v-if="item.duplicate_obtained"
                      name="nrk:media-media-complete"
                    />
                    <Icon
                      v-else="item.duplicate_obtained"
                      name="nrk:media-media-incomplete"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </tbody>
    </table>
  </main>
</template>
