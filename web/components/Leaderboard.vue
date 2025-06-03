<script setup lang="ts">
import { ref, computed } from "vue";

interface RowData {
  index: number;
  rsn: string;
  value: number;
  profile_link: string;
  icon_link: string;
}

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  data: {
    type: Array as () => RowData[],
    required: true,
  },
  metricPage: {
    type: String,
    required: false,
    default: "",
  },
});

const isExpanded = ref(false);
const defaultLimit = 25;

const displayedData = computed(() => {
  return isExpanded.value ? props.data : props.data.slice(0, defaultLimit);
});

const hasMoreEntries = computed(() => {
  return props.data.length > defaultLimit;
});

const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

const formatValue = (value: number): string => {
  return value.toLocaleString();
};
</script>

<template>
  <!-- Main card container: Aggressively smaller max-widths for many cards per row -->
  <div
    class="bg-dc-accent p-1 sm:p-2 rounded-xl shadow-xl w-full
           max-w-[10rem] sm:max-w-[11rem] md:max-w-[12rem] lg:max-w-[13rem] xl:max-w-[14rem] 2xl:max-w-[15rem]"
  >
    <h2 class="text-xs sm:text-sm md:text-base lg:text-lg xl:text-xl font-bold text-white mb-1 sm:mb-2 text-center truncate">
      {{ title }}
      <a
        v-if="metricPage"
        :href="metricPage"
        target="_blank"
        rel="noopener noreferrer"
        class="ml-0.5 text-[0.6rem] sm:text-xs align-middle"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-3 w-3 sm:h-4 sm:w-4 inline-block"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"
          />
          <path
            d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"
          />
        </svg>
      </a>
    </h2>

    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-700">
        <thead class="bg-blurple">
          <tr>
            <th
              scope="col"
              class="px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider rounded-tl-lg"
            >
              Rank
            </th>
            <th
              scope="col"
              class="px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider"
            >
              Player
            </th>
            <th
              scope="col"
              class="px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider rounded-tr-lg"
            >
              Value
            </th>
          </tr>
        </thead>
        <tbody class="bg-dc-accent divide-y divide-gray-700">
          <tr
            v-for="row in displayedData"
            :key="row.index"
            class="hover:bg-gray-700 transition-colors duration-200"
          >
            <td class="px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] font-medium text-white">
              {{ row.index }}
            </td>
            <td class="px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] text-gray-200">
              <a
                :href="row.profile_link"
                target="_blank"
                rel="noopener noreferrer"
                class="flex items-center text-blue-400 hover:text-blue-300"
              >
                <img
                  v-if="row.icon_link"
                  :src="row.icon_link"
                  :alt="`${row.rsn} icon`"
                  class="w-3 h-3 sm:w-4 sm:h-4 rounded-full mr-0.5 sm:mr-1 object-cover"
                />
                <span class="truncate">{{ row.rsn }}</span>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-2.5 w-2.5 sm:h-3 ml-0.5 opacity-75 flex-shrink-0"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"
                  />
                  <path
                    d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"
                  />
                </svg>
              </a>
            </td>
            <td class="px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] text-white">
              {{ formatValue(row.value) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="hasMoreEntries" class="mt-1 sm:mt-2 text-center">
      <button
        @click="toggleExpand"
        class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-0.5 px-1 sm:py-1 sm:px-2 rounded-lg
               focus:outline-none focus:shadow-outline transition-colors duration-200 text-xs sm:text-sm"
      >
        {{ isExpanded ? "Show Less" : `Show All (${props.data.length} entries)` }}
      </button>
    </div>
  </div>
</template>