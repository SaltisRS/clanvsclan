<template>

    <div v-if="isVisible" class="fixed inset bg-dc-accent bg-opacity-95 flex justify-center items-center z-50">
      <div class="bg-dc-background p-6 rounded-lg w-full max-w-xl max-h-[80vh] overflow-y-auto">
        <h3 class="text-lg pt-4 font-semibold mb-6 text-white">Multipliers</h3>
  
        <div v-if="multipliers && multipliers.length > 0">
          <div v-for="(multiplier, index) in multipliers" :key="index" class="border-b border-dc-accent pb-4 mb-4 last:border-b-0 last:mb-0">
            <div class="font-bold text-white">{{ multiplier.name }}</div>
            <div class="text-sm text-gray-300 mb-2">{{ multiplier.description }}</div>
            <div class="text-sm text-white">Factor: {{ multiplier.factor }}x</div>
            <div class="text-sm text-white">Unlocked:
               <span :class="multiplier.unlocked ? 'text-green-500' : 'text-red-500'">
                 {{ multiplier.unlocked ? 'Yes' : 'No' }}
               </span>
            </div>
             <div class="text-sm text-white mt-1">Affects: {{ multiplier.affects.join(',\n') }}</div>
             <div class="text-sm text-white mt-1">Requirements: {{ multiplier.requirement.join(',\n') }}</div>
          </div>
        </div>
        <div v-else>
          <p class="text-white text-center">No multipliers found.</p>
        </div>
  
        <button
          @click="$emit('close')"
          class="absolute top-2 right-2 bg-dc-bg text-white rounded hover:bg-blurple transition-colors duration-200 w-20"
        >
          Close
        </button>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import type { Multiplier } from '../pages/index.vue';
  
  // Define the props the component accepts
  const props = defineProps<{
    isVisible: boolean; // Boolean to control modal visibility
    multipliers: Multiplier[]; // Array of Multiplier objects to display
  }>();
  
  // Define the custom events the component can emit
  const emit = defineEmits(['close']);
  
  // No need for local showMultipliersModal state here, it's controlled by the parent
  </script>