<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Loading, Navbar, Refresh, PointBox, PointsTooltip } from "#components";

interface Multiplier {
  name: string;
  required_items: string;
  factor: number;
  unlocked: boolean;
}

interface Item {
  name: string;
  points: number;
  duplicate_points: number;
  obtained: boolean;
  duplicate_obtained: boolean;
  icon_url: string | null;
}

interface Source {
  name: string;
  source_gained: number;
  items: Item[];
  multipliers: Multiplier[];
  hovertext: string;
  icon_url: string;
}

interface Tier {
  points_gained: number;
  sources: Source[];
}

interface Template {
  associated_team: string;
  total_gained: number;
  tiers: Record<string, Tier>;
}

const activeData = ref<Template>({
  associated_team: "",
  total_gained: 0,
  tiers: {},
});
const team_uris = ["ironfoundry", "ironclad"];
const selectedTier = ref<keyof Template["tiers"]>("Easy");
const selectedTable = ref<string>(team_uris[0]);
const loading = ref<boolean>(false);
const points = ref<number>(0);
const tierPoints = ref<Record<string, number>>({});
const tooltip = ref<{ text: string; x: number; y: number } | null>(null);

onMounted(() => fetchTable(team_uris[0]));

const fetchTable = async (table: string) => {
  console.log("Fetching table data...");
  loading.value = true;

  const minLoadingTime = 200;
  const startTime = Date.now();

  try {
    const response = await fetch(`https://frenzy.ironfoundry.cc/${table}`);
    if (!response.ok) throw new Error("Failed to fetch data");

    const _data = await response.json();
    activeData.value = _data[0];
    selectedTier.value = Object.keys(
      _data[0].tiers
    )[0] as keyof Template["tiers"];

    // ✅ Set total points
    points.value = activeData.value.total_gained;

    // ✅ Extract per-tier points
    tierPoints.value = Object.fromEntries(
      Object.entries(activeData.value.tiers).map(([tier, data]) => [
        tier,
        (data as { points_gained: number }).points_gained,
      ])
    );
  } catch (error) {
    console.error("Error fetching table data:", error);
  } finally {
    const elapsedTime = Date.now() - startTime;
    const remainingTime = minLoadingTime - elapsedTime;
    setTimeout(() => {
      loading.value = false;
    }, remainingTime);
  }
};

// Text Highlighting
const isSourceFullyObtained = (source: Source) => {
  return source.items.every((item) => item.obtained && item.duplicate_obtained);
};
// Text Highlighting
const isSourcePartiallyObtained = (source: Source) => {
  return source.items.some((item) => item.obtained || item.duplicate_obtained);
};

// Table Logic
const showDetails = (event: MouseEvent) => {
  const target = event.currentTarget as HTMLElement;
  const table = target.querySelector("td.details-cell table");

  if (table) {
    table.classList.toggle("hidden");
  }
};

//Table Tooltips
const showTooltip = (event: MouseEvent, text: string | undefined) => {
  if (!text) return;

  if (text) {
    tooltip.value = { text, x: event.clientX, y: event.clientY };
  }
};

const updateTooltipPosition = (event: MouseEvent) => {
  if (!tooltip.value) return;

  if (tooltip.value) {
    tooltip.value.x = event.clientX;
    tooltip.value.y = event.clientY - 15;
  }
};

const hideTooltip = () => {
  tooltip.value = null;
};
</script>

<template>
  <main
    class="flex flex-col justify-center items-center p-20 gap-8 select-none"
  >
    <div v-if="loading">
      <Loading />
    </div>

    <div>
      <Navbar />
    </div>

    <div>
      <Refresh class="z-50" @click="() => fetchTable(selectedTable)"></Refresh>
    </div>
    <div
      v-if="!loading"
      class="fixed top-16 left-2 opacity-50 z-50 flex flex-col items-start space-y-2"
    >
      <div class="flex items-center">
        <Icon name="nrk:radio-active" class="text-green-500" />
        <span class="ml-2 text-sm text-green-500">Full Completion</span>
      </div>
      <div class="flex items-center">
        <Icon name="nrk:radio-active" class="text-yellow-500" />
        <span class="ml-2 text-sm text-yellow-500">Partial Completion</span>
      </div>
    </div>

    <div v-if="!loading" class="z-50">
      <PointsTooltip :position="'top'" :tiers="tierPoints">
        <PointBox :points="points" />
      </PointsTooltip>
    </div>

    <!-- Image Buttons -->
    <div v-if="!loading && activeData" class="flex gap-40">
      <img
        v-for="table in team_uris"
        :key="table"
        :src="`${table}.png`"
        @click="
          () => {
            selectedTable = table;
            fetchTable(table);
          }
        "
        class="size-40 rounded-full border-4 cursor-pointer transition-all duration-200"
        :class="
          selectedTable === table
            ? 'border-blurple shadow-lg scale-110'
            : 'border-white opacity-70 hover:opacity-100'
        "
      />
    </div>

    <!-- Tier Buttons -->
    <div v-if="!loading && activeData" class="flex gap-4">
      <button
        v-for="(_, key) in activeData.tiers"
        :key="key"
        @click="selectedTier = key"
        :class="selectedTier === key ? 'text-blurple' : 'text-white'"
        class="bg-dc-accent px-4 py-2 rounded-lg border border-black"
      >
        {{ key }}
      </button>
    </div>

    <!-- Divider -->
    <div v-if="!loading" class="flex w-[97%] items-center">
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Left Border -->
      <span class="px-12 text-center text-xl">Sources</span>
      <!-- Text -->
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Right Border -->
    </div>

    <!-- Main Table -->
    <table
      v-if="!loading && activeData"
      class="bg-dc-accent w-full rounded-xl overflow-hidden"
    >
      <thead>
        <tr>
          <th class="p-2 w-1/5">Name</th>
          <th class="p-2 w-4/5">Details</th>
        </tr>
      </thead>
      <tbody v-if="activeData.tiers[selectedTier]">
        <tr
          v-for="(source, key) in (activeData.tiers[selectedTier] as Tier)?.sources"
          :key="key"
          class="border-t border-black hover:bg-blurple/25 cursor-pointer transition-all duration-200"
          @click="showDetails"
          @mouseenter="showTooltip($event, source.hovertext)"
          @mouseleave="hideTooltip"
          @mousemove="updateTooltipPosition"
        >
          <td
            class="px-4"
            :class="{
              'text-green-500': isSourceFullyObtained(source),
              'text-yellow-500': isSourcePartiallyObtained(source),
              'text-white': !isSourcePartiallyObtained(source),
            }"
          >
            {{ source.name }}
          </td>
          <td class="details-cell">
            <table class="hidden w-full table-fixed">
              <thead>
                <tr>
                  <th class="w-1/5 p-1">Name</th>
                  <th class="w-1/5 p-1">Points</th>
                  <th class="w-1/5 p-1">Dupe Points</th>
                  <th class="w-1/5 p-1">Obtained</th>
                  <th class="w-1/5 p-1">Dupe Obtained</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, key) in source.items"
                  :key="key"
                  :class="{
                    'text-yellow-500':
                      item.obtained && !item.duplicate_obtained,
                    'text-green-500': item.obtained && item.duplicate_obtained,
                    'text-white': !item.obtained,
                  }"
                >
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
                      class="text-green-500"
                    />
                    <Icon
                      v-else="item.obtained"
                      name="nrk:media-media-incomplete"
                      class="text-red-500"
                    />
                  </td>
                  <td class="text-center p-1">
                    <Icon
                      v-if="item.duplicate_obtained"
                      name="nrk:media-media-complete"
                      class="text-green-500"
                    />
                    <Icon
                      v-else="item.duplicate_obtained"
                      name="nrk:media-media-incomplete"
                      class="text-red-500"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Divider -->
    <div v-if="!loading" class="flex w-[97%] items-center">
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Left Border -->
      <span class="px-12 text-center text-xl">Multipliers</span>
      <!-- Text -->
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Right Border -->
    </div>

    <!-- Multipliers Table -->
    <table v-if="!loading && activeData" class="w-full bg-dc-accent rounded-xl">
      <thead>
        <tr class="text-center">
          <th class="w-1/5 py-1">Source</th>
          <th class="w-1/5 py-1">Description</th>
          <th class="w-1/5 py-1">Factor</th>
          <th class="w-1/5 py-1">Required Items</th>
          <th class="w-1/5 py-1">Unlocked</th>
        </tr>
      </thead>
      <tbody>
        <template
          v-for="source in (activeData.tiers[selectedTier] as Tier)?.sources"
          :key="source.name"
        >
          <template v-if="source.multipliers.length">
            <tr
              v-for="multiplier in source.multipliers"
              :key="multiplier.name"
              class="text-center"
            >
              <td
                class="p-2"
                :class="{
                  'text-green-500': multiplier.unlocked,
                  'text-white': !multiplier.unlocked,
                }"
              >
                {{ source.name }}
              </td>
              <td
                class="p-2"
                :class="{
                  'text-green-500': multiplier.unlocked,
                  'text-white': !multiplier.unlocked,
                }"
              >
                {{ multiplier.name }}
              </td>
              <td
                class="p-2"
                :class="{
                  'text-green-500': multiplier.unlocked,
                  'text-white': !multiplier.unlocked,
                }"
              >
                {{ multiplier.factor }}
              </td>
              <td
                class="p-2"
                :class="{
                  'text-green-500': multiplier.unlocked,
                  'text-white': !multiplier.unlocked,
                }"
              >
                <ul>
                  <li
                    v-for="(item, index) in multiplier.required_items.split(
                      ','
                    )"
                    :key="index"
                  >
                    {{ item }}
                  </li>
                </ul>
              </td>
              <td class="p-2">
                <Icon
                  v-if="multiplier.unlocked"
                  name="nrk:media-media-complete"
                  class="text-green-500"
                />
                <Icon
                  v-else="!multiplier.unlocked"
                  name="nrk:media-media-incomplete"
                />
              </td>
            </tr>
          </template>
        </template>
      </tbody>
    </table>

    <!-- Tooltip Display -->
    <div
      v-if="tooltip"
      class="fixed bg-blurple text-white text-sm px-2 py-1 rounded shadow-lg pointer-events-none"
      :style="{ top: `${tooltip.y - 15}px`, left: `${tooltip.x}px` }"
    >
      {{ tooltip.text }}
    </div>
  </main>
</template>
