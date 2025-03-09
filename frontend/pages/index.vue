<script setup lang="ts">
import data from '../Frenzy.Templates.json'

const prepareData = data[0]
const selectedTier = ref<keyof typeof prepareData.tiers>('Easy')

const showDetails = (source: MouseEvent) => {
  const target = source.currentTarget as HTMLElement
  const table = target.querySelector('td.details-cell table')

  if (table && table.classList.contains('hidden')) {
    table.classList.remove('hidden')
  } else if (table) {
    table.classList.add('hidden')
  }
}
</script>

<template>
  <main class="flex flex-col justify-center items-center p-20 gap-10">
    <div class="flex gap-4">
      <button
        v-for="(_, key) in prepareData.tiers"
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
          v-for="(source, key) in prepareData.tiers[selectedTier].sources"
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
                <tr
                  v-for="(item, key) in source.items"
                  :key="key"
                >
                  <td class="p-1">{{ item.name }}</td>
                  <td class="text-center p-1">{{ item.points }}</td>
                  <td class="text-center p-1">{{ item.duplicate_points }}</td>
                  <td class="text-center p-1">
                    <Icon v-if="item.obtained" name="nrk:media-media-complete" />
                    <Icon v-else="item.obtained" name="nrk:media-media-incomplete" />
                  </td>
                  <td class="text-center p-1">
                    <Icon v-if="item.duplicate_obtained" name="nrk:media-media-complete" />
                    <Icon v-else="item.duplicate_obtained" name="nrk:media-media-incomplete" />
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