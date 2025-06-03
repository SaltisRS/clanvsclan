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
  <!-- Main card container: Adjusted widths for more cards per row -->
  <div
    class="bg-dc-accent p-2 rounded-xl shadow-xl w-full
           max-w-xs sm:max-w-sm md:max-w-md lg:max-w-md xl:max-w-sm 2xl:max-w-xs"
  >
    <h2 class="text-2xl font-bold text-white mb-4 text-center">
      {{ title }}
      <a
        v-if="metricPage"
        :href="metricPage"
        target="_blank"
        rel="noopener noreferrer"
        class="ml-2 text-blue-400 hover:text-blue-300 text-base align-middle"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 inline-block"
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
              class="px-3 py-2 text-left text-xs font-medium text-white uppercase tracking-wider rounded-tl-lg"
            >
              Rank
            </th>
            <th
              scope="col"
              class="px-3 py-2 text-left text-xs font-medium text-white uppercase tracking-wider"
            >
              Player
            </th>
            <th
              scope="col"
              class="px-3 py-2 text-left text-xs font-medium text-white uppercase tracking-wider rounded-tr-lg"
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
            <td class="px-3 py-2 whitespace-nowrap text-sm font-medium text-white">
              {{ row.index }}
            </td>
            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-200">
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
                  class="w-6 h-6 rounded-full mr-2 object-cover"
                />
                {{ row.rsn }}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  class="h-4 w-4 ml-1 opacity-75"
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
            <td class="px-3 py-2 whitespace-nowrap text-sm text-white">
              {{ formatValue(row.value) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="hasMoreEntries" class="mt-4 text-center">
      <button
        @click="toggleExpand"
        class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg
               focus:outline-none focus:shadow-outline transition-colors duration-200"
      >
        {{ isExpanded ? "Show Less" : `Show All (${props.data.length} entries)` }}
      </button>
    </div>
  </div>
</template>