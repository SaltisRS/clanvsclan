<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  Loading,
  Navbar,
  Refresh,
  PointBox,
  PointsTooltip,
  MultiModal,
} from "#components";

interface Item {
  name: string;
  points: number;
  duplicate_points: number;
  required: number;
  duplicate_required: number;
  obtained: number;
  icon_url: string | null;
}

interface Source {
  name: string;
  source_gained: number;
  items: Item[];
  hovertext: string;
  icon_url: string;
}

interface Tier {
  points_gained: number;
  sources: Source[];
}

interface Activity {
  name: string;
  current_value: number;
  point_step: number;
  tier1: number;
  tier2: number;
  tier3: number;
  tier4: number;
  multiplier: number;
  unit: string;
  req_factor: number;
}

interface Milestone {
  name: string;
  current_value: number;
  point_step: number;
  tier1: number;
  tier2: number;
  tier3: number;
  tier4: number;
  multiplier: number;
  unit: string;
  req_factor: number;
}

interface Screenshot {
  name: string;
  start: string;
  end?: string;
}

interface TimestampObject {
  $date: string;
}

interface TrackingEntry {
  name: string;
  start: {
    screenshot: string;
    values: Record<string, number>;
    timestamp: TimestampObject;
  };
  end: {
    screenshot?: string;
    values?: Record<string, number>; // Use the TrackingValues interface
    timestamp: TimestampObject | null; // Timestamp can be null for the end
  };
}

export interface Multiplier {
  name: string;
  description: string;
  affects: string[];
  factor: number;
  requirement: string[];
  unlocked: boolean;
}

interface Template {
  associated_team: string;
  total_gained: number;
  tiers: Record<string, Tier>;
  multipliers: Multiplier[];
  activities: Activity[];
  milestones: Record<string, Milestone[]>;
}

const activeData = ref<Template>({
  associated_team: "",
  total_gained: 0,
  tiers: {},
  multipliers: [],
  activities: [],
  milestones: {},
});

interface ActivityOrMilestone {
  name: string;
  current_value: number;
  point_step: number;
  tier1: number;
  tier2: number;
  tier3: number;
  tier4: number;
  multiplier: number;
  unit: string;
  req_factor: number;
}

const calculateEntryPoints = (entry: ActivityOrMilestone): number => {
  const currentValue = entry.current_value;
  const pointStep = entry.point_step;
  const tier1 = entry.tier1 * entry.req_factor;
  const tier2 = entry.tier2 * entry.req_factor;
  const tier3 = entry.tier3 * entry.req_factor;
  const tier4 = entry.tier4 * entry.req_factor;
  const multiplier = entry.multiplier;

  let tiers_completed = 0;


  if (currentValue >= tier1) {
    tiers_completed++;
  }
  if (currentValue >= tier2) {
    tiers_completed++;
  }
  if (currentValue >= tier3) {
    tiers_completed++;
  }
  if (currentValue >= tier4) {
    tiers_completed++;
  }


  let base_points = pointStep * tiers_completed;


  if (currentValue >= tier4) {
    return base_points * multiplier;
  } else {
    return base_points;
  }
};

// Computed property to calculate total points from Activities
const totalActivityPoints = computed(() => {
  if (!activeData.value || !activeData.value.activities) return 0;

  let total = 0;
  for (const activity of activeData.value.activities) {
    total += calculateEntryPoints(activity);
  }
  return total;
});

// Computed property to calculate total points from Milestones
const totalMilestonePoints = computed(() => {
  if (!activeData.value || !activeData.value.milestones) return 0;

  let total = 0;
  // Milestones are nested by category
  for (const categoryName in activeData.value.milestones) {
    const milestonesInCategory = activeData.value.milestones[categoryName];
    if (milestonesInCategory && milestonesInCategory.length > 0) {
      for (const milestone of milestonesInCategory) {
        total += calculateEntryPoints(milestone);
      }
    }
  }
  return total;
});

const combinedTotalPoints = computed(() => {
  // activeData.value.total_gained is points from Sources
  return (
    activeData.value.total_gained +
    totalActivityPoints.value +
    totalMilestonePoints.value
  );
});

const team_uris = ["ironfoundry", "ironclad"];
const selectedTier = ref<keyof Template["tiers"]>("Easy");
const selectedTable = ref<string>(team_uris[0]);
const loading = ref<boolean>(false);
const tierPoints = ref<Record<string, number>>({});
const tooltip = ref<{ text: string; x: number; y: number } | null>(null);
const isCollapsedActivities = ref<boolean>(true);
const showMultipliersModal = ref<boolean>(false);

const isSourceObtained = (source: Source): boolean => {
  return Object.values(source.items).some((item) => item.obtained > 0);
};

// Helper function to check if a source is fully obtained for the current team
const isSourceFullyObtained = (source: Source): boolean => {
  // Check if all items in the source meet their individual requirements
  return Object.values(source.items).every(
    (item) =>
      item.obtained >= item.required && // Unique requirement met
      item.obtained - item.required >= item.duplicate_required // Duplicate requirement met
  );
};

// Helper function to get the class for a source row
const getSourceRowClass = (source: Source): string => {
  if (isSourceFullyObtained(source)) {
    return "text-green-500";
  } else if (isSourceObtained(source)) {
    return "text-yellow-500";
  } else {
    return "text-white";
  }
};

// Helper function to get the class for an item cell
const getItemCellClass = (item: Item): string => {
  const uniqueObtained = Math.min(item.obtained, item.required);
  const duplicateObtained = Math.max(0, item.obtained - item.required); // Duplicates obtained after getting unique

  // Case 1: Fully obtained (unique met AND duplicate requirement met)
  if (
    uniqueObtained >= item.required &&
    duplicateObtained >= item.duplicate_required
  ) {
    return "text-green-500";
  }
  // Case 2: Partially obtained (at least one obtained, but not fully)
  else if (item.obtained > 0) {
    return "text-yellow-500";
  }
  // Case 3: Not obtained
  else {
    return "text-white";
  }
};

// Helper function to display unique obtained
const getUniqueObtainedDisplay = (item: Item): string => {
  return `${Math.min(item.obtained, item.required)}/${item.required}`;
};

// Helper function to display duplicate obtained
const getDuplicateObtainedDisplay = (item: Item): string => {
  if (item.obtained >= item.required) {
    const duplicateProgress = item.obtained - item.required;
    return `${duplicateProgress}/${item.duplicate_required}`;
  } else {
    return `0/${item.duplicate_required}`;
  }
};

const teamItemObtainedCounts = computed<Record<string, number>>(() => {
  const obtainedMap: Record<string, number> = {};
  if (!activeData.value || !activeData.value.tiers) return obtainedMap;

  // Iterate through all items in the template structure
  for (const tierName in activeData.value.tiers) {
    const tierData = activeData.value.tiers[tierName];
    if (tierData && tierData.sources) {
      for (const source of tierData.sources) {
        if (source.items) {
          for (const item of source.items) {
            if (item.name) {
              obtainedMap[item.name] = item.obtained; // Store obtained count by item name
            }
          }
        }
      }
    }
  }
  return obtainedMap;
});

const toggleCollapseActivities = () => {
  isCollapsedActivities.value = !isCollapsedActivities.value;
};

onMounted(() => fetchTable(team_uris[0]));

const fetchTable = async (table: string) => {
  console.log("Fetching table data...");
  loading.value = true;

  const startTime = Date.now();

  try {
    const response = await fetch(`https://frenzy.ironfoundry.cc/${table}`);
    if (!response.ok) throw new Error("Failed to fetch data");

    const _data = await response.json();
    activeData.value = _data[0];
    selectedTier.value = Object.keys(
      _data[0].tiers
    )[0] as keyof Template["tiers"];

    tierPoints.value = Object.fromEntries(
      Object.entries(activeData.value.tiers).map(([tier, data]) => [
        tier,
        (data as { points_gained: number }).points_gained,
      ])
    );

if (activeData.value) {
      // Total points from all Activities
      const totalActivities = totalActivityPoints.value;
      if (totalActivities > 0) {
          tierPoints.value["Activities"] = totalActivities;
      }


      // Total points for each Milestone category
      for (const categoryName in activeData.value.milestones) {
        const milestonesInCategory = activeData.value.milestones[categoryName];
        if (milestonesInCategory && milestonesInCategory.length > 0) {
          let categoryTotal = 0;
          for (const milestone of milestonesInCategory) {
            categoryTotal += calculateEntryPoints(milestone);
          }
          if (categoryTotal > 0) {
            const displayCategoryName = getDisplayCategoryName(categoryName);
            tierPoints.value[displayCategoryName] = categoryTotal; // Append category total
          }
        }
      }
    }


  } catch (error) {
    console.error("Error fetching table data:", error);
  } finally {
      loading.value = false;
  }
};

const getTierColorActivity = (activity: Activity, tierNumber: number) => {
  const currentValue = activity.current_value;
  const tierValue = activity[`tier${tierNumber}` as keyof Activity] as number;
  const previousTierValue = (
    tierNumber > 1 ? activity[`tier${tierNumber - 1}` as keyof Activity] : 0
  ) as number;

  // If the current value is at or above this tier, it's green
  if (currentValue >= tierValue) {
    return "text-green-500";
  }

  // If the current value is below this tier but at or above the previous tier (or greater than 0 for tier 1), it's yellow
  if (currentValue >= previousTierValue && currentValue < tierValue) {
    // Special case for Tier 1: current_value needs to be > 0 and < tier1
    if (tierNumber === 1 && currentValue > 0 && currentValue < tierValue) {
      return "text-yellow-500";
    }
    // For tiers 2, 3, and 4, it just needs to be >= the previous tier and < this tier
    if (
      tierNumber > 1 &&
      currentValue >= previousTierValue &&
      currentValue < tierValue
    ) {
      return "text-yellow-500";
    }
  }

  // If none of the above, it's white (below the first tier requirement or 0)
  return "text-white";
};

const categoryDisplayNameMap: Record<string, string> = {
  cluescroll: "Clue Scrolls",
  experience: "Experience",
  killcount: "Kill Count",
};

const getDisplayCategoryName = (categoryName: string): string => {
  return categoryDisplayNameMap[categoryName] || categoryName;
};

const getTierColorMilestone = (
  milestone: Milestone,
  tierNumber: number
): string => {
  const currentValue = milestone.current_value;
  const tierValue = milestone[`tier${tierNumber}` as keyof Milestone] as number;
  const previousTierValue = (
    tierNumber > 1 ? milestone[`tier${tierNumber - 1}` as keyof Milestone] : 0
  ) as number;

  // If the current value is at or above this tier, it's green
  if (currentValue >= tierValue) {
    return "text-green-500";
  }

  // If the current value is below this tier but at or above the previous tier (or greater than 0 for tier 1), it's yellow
  if (currentValue >= previousTierValue && currentValue < tierValue) {
    // Special case for Tier 1: current_value needs to be > 0 and < tier1
    if (tierNumber === 1 && currentValue > 0 && currentValue < tierValue) {
      return "text-yellow-500";
    }
    // For tiers 2, 3, and 4, it just needs to be >= the previous tier and < this tier
    if (
      tierNumber > 1 &&
      currentValue >= previousTierValue &&
      currentValue < tierValue
    ) {
      return "text-yellow-500";
    }
  }

  // If none of the above, it's white (below the first tier requirement or 0)
  return "text-white";
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
      <button
        @click="showMultipliersModal = true"
        class="mb-4 px-4 py-2 bg-dc-accent text-white rounded-xl hover:bg-blurple transition-colors duration-200"
      >
        Show Multipliers
      </button>
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

<MultiModal
      :isVisible="showMultipliersModal"
      :multipliers="activeData?.multipliers || []"
      :teamObtainedItems="teamItemObtainedCounts"
      @close="showMultipliersModal = false"
    />

    <div v-if="!loading" class="z-50">
      <PointsTooltip :position="'top'" :tiers="tierPoints">
        <PointBox :points="combinedTotalPoints" />
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

    <!-- Main Table (Sources) -->
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
          <td class="px-4">
            <!-- Apply the color class to an inner span -->
            <span :class="getSourceRowClass(source)">
              {{ source.name }}
            </span>
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
                  :class="getItemCellClass(item)"
                >
                  <td class="p-1">{{ item.name }}</td>
                  <td class="text-center p-1">
                    {{ item.points }}
                  </td>
                  <td class="text-center p-1">
                    {{ item.duplicate_points }}
                  </td>
                  <td class="text-center p-1">
                    {{ getUniqueObtainedDisplay(item) }}
                  </td>
                  <td class="text-center p-1">
                    {{ getDuplicateObtainedDisplay(item) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </td>
        </tr>
      </tbody>
      <tbody v-else>
        <tr>
          <td colspan="2" class="py-4 text-center">
            No items found for this tier.
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Divider -->
    <div v-if="!loading" class="flex w-[97%] items-center">
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Left Border -->
      <span class="px-12 text-center text-xl">Activities</span>
      <!-- Text -->
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Right Border -->
    </div>

    <div class="w-full">
      <table
        v-if="!loading && activeData"
        class="bg-dc-accent w-full rounded-xl overflow-hidden"
      >
        <thead>
          <tr>
            <th class="p-2 w-1/5 text-center">Activity</th>
            <th class="p-2 w-4/5 text-center relative">
              Details
              <button
                @click="toggleCollapseActivities"
                class="absolute top-1/2 right-2 transform -translate-y-1/2 px-2 py-1 text-xs bg-blurple text-white hover:bg-dc-accent transition-colors duration-200 z-10 rounded-xl"
              >
                {{ isCollapsedActivities ? "Show" : "Hide" }}
              </button>
            </th>
          </tr>
        </thead>

        <tbody
          v-if="
            !isCollapsedActivities &&
            activeData.activities &&
            activeData.activities.length > 0
          "
        >
          <tr
            v-for="activity in activeData.activities"
            :key="activity.name"
            class="border-t border-black hover:bg-blurple/25 cursor-pointer transition-all duration-200"
          >
            <td class="p-2 w-1/5 font-bold">
              {{ activity.name }}
            </td>
            <td class="p-2 w-4/5 text-white">
              <table class="w-full table-fixed">
                <thead>
                  <tr>
                    <th class="w-1/6 p-1 text-center">Progress</th>
                    <th class="w-1/6 p-1 text-center">Points / Tier</th>
                    <th class="w-1/6 p-1 text-center">T1</th>
                    <th class="w-1/6 p-1 text-center">T2</th>
                    <th class="w-1/6 p-1 text-center">T3</th>
                    <th class="w-1/6 p-1 text-center">T4</th>
                    <th class="w-1/6 p-1 text-center">T4 Multiplier</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="text-center p-1">
                      {{ activity.current_value }} {{ activity.unit }}
                    </td>
                    <td class="text-center p-1">
                      {{ activity.point_step }}
                    </td>
                    <td
                      :class="[
                        'text-center',
                        'p-1',
                        getTierColorActivity(activity, 1),
                      ]"
                    >
                      {{ activity.tier1 * activity.req_factor }}
                    </td>
                    <td
                      :class="[
                        'text-center',
                        'p-1',
                        getTierColorActivity(activity, 2),
                      ]"
                    >
                      {{ activity.tier2 * activity.req_factor }}
                    </td>
                    <td
                      :class="[
                        'text-center',
                        'p-1',
                        getTierColorActivity(activity, 3),
                      ]"
                    >
                      {{ activity.tier3 * activity.req_factor }}
                    </td>
                    <td
                      :class="[
                        'text-center',
                        'p-1',
                        getTierColorActivity(activity, 4),
                      ]"
                    >
                      {{ activity.tier4 * activity.req_factor }}
                    </td>
                    <td class="text-center p-1">{{ activity.multiplier }}x</td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </tbody>
        <tbody
          v-else-if="
            isCollapsedActivities &&
            activeData.activities &&
            activeData.activities.length > 0
          "
        >
          <tr>
            <td colspan="2" class="py-4 text-center">
              Activities table is collapsed. Click "Show" to view activities.
            </td>
          </tr>
        </tbody>

        <tbody v-else>
          <tr>
            <td colspan="2" class="py-4 text-center">No activities found.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Divider -->
    <div v-if="!loading" class="flex w-[97%] items-center">
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Left Border -->
      <span class="px-12 text-center text-xl">Milestones</span>
      <!-- Text -->
      <div class="flex-1 border-t border-blurple"></div>
      <!-- Right Border -->
    </div>

    <div
      v-if="!loading && activeData && activeData.milestones"
      class="items-center"
    >
      <div
        v-for="(milestonesInCategory, categoryName) in activeData.milestones"
        :key="categoryName"
        class="mb-6 w-full"
      >
        <span class="text-lg mb-2 w-full text-center text-white">
          {{ getDisplayCategoryName(categoryName) }}
        </span>

        <table class="bg-dc-accent w-full rounded-xl overflow-hidden">
          <thead>
            <tr>
              <th class="p-2 w-1/5 text-center">Milestone</th>
              <th class="p-2 w-4/5 text-center">Details</th>
            </tr>
          </thead>
          <tbody v-if="milestonesInCategory && milestonesInCategory.length > 0">
            <tr
              v-for="milestone in milestonesInCategory"
              :key="milestone.name"
              class="border-t border-black hover:bg-blurple/25 cursor-pointer transition-all duration-200"
            >
              <td class="p-2 w-1/5 font-bold text-center">
                {{ milestone.name }}
              </td>
              <td class="p-2 w-4/5 text-white">
                <table class="w-full table-fixed">
                  <thead>
                    <tr>
                      <th class="w-1/6 p-1 text-center">Progress</th>
                      <th class="w-1/6 p-1 text-center">Points / Tier</th>
                      <th class="w-1/6 p-1 text-center">T1</th>
                      <th class="w-1/6 p-1 text-center">T2</th>
                      <th class="w-1/6 p-1 text-center">T3</th>
                      <th class="w-1/6 p-1 text-center">T4</th>
                      <th class="w-1/6 p-1 text-center">T4 Multiplier</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td class="text-center p-1">
                        {{ milestone.current_value }} {{ milestone.unit }}
                      </td>
                      <td class="text-center p-1">
                        {{ milestone.point_step }}
                      </td>
                      <td
                        :class="[
                          'text-center',
                          'p-1',
                          getTierColorMilestone(milestone, 1),
                        ]"
                      >
                        {{ milestone.tier1 * milestone.req_factor }}
                        {{ milestone.unit }}
                      </td>
                      <td
                        :class="[
                          'text-center',
                          'p-1',
                          getTierColorMilestone(milestone, 2),
                        ]"
                      >
                        {{ milestone.tier2 * milestone.req_factor }}
                        {{ milestone.unit }}
                      </td>
                      <td
                        :class="[
                          'text-center',
                          'p-1',
                          getTierColorMilestone(milestone, 3),
                        ]"
                      >
                        {{ milestone.tier3 * milestone.req_factor }}
                        {{ milestone.unit }}
                      </td>
                      <td
                        :class="[
                          'text-center',
                          'p-1',
                          getTierColorMilestone(milestone, 4),
                        ]"
                      >
                        {{ milestone.tier4 * milestone.req_factor }}
                        {{ milestone.unit }}
                      </td>
                      <td class="text-center p-1">
                        {{ milestone.multiplier }}x
                      </td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="2" class="py-4 text-center">
                No milestones found in this category.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

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
