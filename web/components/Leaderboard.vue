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

const formatValue = (value: number): string => {
  return value.toLocaleString();
};

const columnWidths = {
  rank: "w-[20%]",
  player: "w-[60%]",
  value: "w-[20%]",
};
</script>

<template>
  <div
    class="bg-dc-accent p-1 sm:p-2 rounded-xl shadow-xl w-full max-w-[13rem] sm:max-w-[15rem] md:max-w-[17rem] lg:max-w-[19rem] xl:max-w-[21rem] 2xl:max-w-[23rem] flex flex-col"
  >
    v-if="metricPage" :href="metricPage"
    <a
      target="_blank"
      rel="noopener noreferrer"
      class="ml-0.5 text-[0.6rem] sm:text-xs align-middle"
    >
      <h2
        class="text-xs sm:text-sm md:text-base lg:text-lg xl:text-xl font-bold text-white mb-1 sm:mb-2 text-center truncate"
      >
        {{ title }}
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
      </h2>
    </a>

    <div class="flex-grow">
      <table class="min-w-full divide-y divide-gray-700 table-fixed">
        <thead class="bg-blurple">
          <tr>
            <th
              scope="col"
              :class="[
                columnWidths.rank,
                'px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider rounded-tl-lg',
              ]"
            >
              Rank
            </th>
            <th
              scope="col"
              :class="[
                columnWidths.player,
                'px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider',
              ]"
            >
              Player
            </th>
            <th
              scope="col"
              :class="[
                columnWidths.value,
                'px-1 py-0.5 text-left text-[0.55rem] sm:text-[0.6rem] font-medium text-white uppercase tracking-wider rounded-tr-lg',
              ]"
            >
              Value
            </th>
          </tr>
        </thead>
      </table>

      <div
        class="bg-dc-accent divide-y divide-gray-700 max-h-64 sm:max-h-80 overflow-y-auto"
      >
        <table class="min-w-full divide-y divide-gray-700 table-fixed">
          <tbody>
            <tr
              v-for="row in data"
              :key="row.index"
              class="hover:bg-gray-700 transition-colors duration-200"
            >
              <td
                :class="[
                  columnWidths.rank,
                  'px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] font-medium text-white',
                ]"
              >
                {{ row.index }}
              </td>
              <td
                :class="[
                  columnWidths.player,
                  'px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] text-gray-200',
                ]"
              >
                <a
                  :href="row.profile_link"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center text-blue-400 hover:text-blue-300 min-w-0"
                >
                  <img
                    v-if="row.icon_link"
                    :src="row.icon_link"
                    :alt="`${row.rsn} icon`"
                    class="w-3 h-3 sm:w-4 sm:h-4 rounded-full mr-0.5 sm:mr-1 object-cover flex-shrink-0"
                  />
                  <span class="truncate flex-grow">{{ row.rsn }}</span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-3 w-3 ml-0.5 opacity-75 flex-shrink-0"
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
              <td
                :class="[
                  columnWidths.value,
                  'px-1 py-0.5 whitespace-nowrap text-[0.6rem] sm:text-[0.7rem] text-white',
                ]"
              >
                {{ formatValue(row.value) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
