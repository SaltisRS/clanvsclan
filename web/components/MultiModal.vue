<template>
    <div v-if="isVisible" class="fixed inset-16 bg-dc-accent bg-opacity-95 flex justify-center items-center z-50">
      <div class="bg-dc-background p-6 rounded-lg w-full max-w-full max-h-full overflow-y-auto">
        <!-- This loop now correctly knows 'multiplier' is a Multiplier object -->
        <div v-if="multipliers && multipliers.length > 0">
            <div class="pb-4 mb-4">
                <div class="font-bold text-xl">Frenzy Multiplier</div>
                <div class="text-sm text-gray-300 mb-2">Frenzy unlocks when a Source has all of its items unlocked.</div>
                <div class="text-sm">This comes with a *1.25x Multiplier* to that source.</div>
                <div class="text-sm">Miscellaneous has some special Frenzy's that are explicitly shown in this list.</div>
            </div>
          <div v-for="(multiplier, index) in multipliers" :key="index" class="border-b w-full border-dc-accent pb-4 mb-4 last:border-b-0 last:mb-0">
            <div class="font-bold text-white">{{index + ". " + multiplier.name }}</div>
            <div class="text-md text-gray-300 mb-2">{{ multiplier.description }}</div>
            <div class="text-md text-white">Factor: {{ multiplier.factor }}x</div>
            <div class="text-md text-white">Unlocked:
               <span :class="multiplier.unlocked ? 'text-green-500' : 'text-red-500'">
                 {{ multiplier.unlocked ? 'Yes' : 'No' }}
               </span>
            </div>
             <div class="text-sm text-white mt-1">Affects: {{ multiplier.affects.join(', ') }}</div>

             <!-- Display Requirements with highlighting -->
             <div v-if="multiplier.requirement && multiplier.requirement.length > 0" class="text-sm text-white mt-1">
                Requirements:
                <span v-for="(req_item_name, req_index) in multiplier.requirement" :key="req_index">
                    <!-- Apply class based on whether the item is obtained -->
                    <span :class="isRequirementObtained(req_item_name) ? 'text-green-500 font-bold' : 'text-red-500'">
                        {{ req_item_name }}
                    </span>
                    <span v-if="req_index < multiplier.requirement.length - 1">, </span>
                </span>
             </div>

          </div>
        </div>
        <div v-else>
          <p class="text-white text-center">No multipliers found.</p>
        </div>
        <button
          @click="$emit('close')"
          class="absolute top-2 right-2 bg-dc-bg text-white rounded hover:bg-blurple transition-colors duration-200 w-28 h-7"
        >
          Close
        </button>
      </div>
    </div>
  </template>

  <script setup lang="ts">
  import type { Multiplier } from '../pages/index.vue';
  import type { PropType } from 'vue';

  const props = defineProps({
    isVisible: Boolean,
    multipliers: {
        type: Object as PropType<Multiplier[]>,
        default: () => [],
    },
    teamObtainedItems: {
      type: Object as PropType<Record<string, number>>,
      default: () => ({}),
    },
  });

  // Define the custom events the component can emit
  const emit = defineEmits(['close']);

  // Helper function to check if a requirement item is obtained (remains the same)
  const isRequirementObtained = (item_name: string): boolean => {
    // Check if the item name exists in the teamObtainedItems data and its count is > 0
    return props.teamObtainedItems[item_name] > 0;
  };

  </script>
