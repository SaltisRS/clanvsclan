<template>
    <div 
      class="relative inline-block"
      @mouseenter="startTracking"
      @mouseleave="stopTracking"
    >
      <!-- Slot wraps the component -->
      <slot></slot>
  
      <!-- Tooltip box -->
      <div
        v-if="visible"
        ref="tooltip"
        class="fixed z-50 bg-blurple text-black font-mono text-sm p-2 rounded shadow-lg pointer-events-none"
        :style="{ top: tooltipY + 'px', left: tooltipX + 'px' }"
      >
        <div v-for="(tierPoints, tier) in tiers" :key="tier">
          <span class="font-bold">{{ tier }}:</span> {{ tierPoints }} points
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import { ref } from "vue";
  
  defineProps<{ tiers: Record<string, number> }>();
  
  const tooltip = ref<HTMLElement | null>(null);
  const tooltipX = ref(0);
  const tooltipY = ref(0);
  const visible = ref(false);
  
  const startTracking = (event: MouseEvent) => {
    visible.value = true;
    moveTooltip(event);
  
    document.addEventListener("mousemove", moveTooltip);
  };
  
  const stopTracking = () => {
    visible.value = false;
    document.removeEventListener("mousemove", moveTooltip);
  };
  
  const moveTooltip = (event: MouseEvent) => {
    const offset = 5; // Gap between cursor and tooltip
  
    let newX = event.clientX + offset;
    let newY = event.clientY + offset;
  
    // Get viewport width & height
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
  
    // Get tooltip dimensions (if available)
    const tooltipWidth = tooltip.value?.offsetWidth || 0;
    const tooltipHeight = tooltip.value?.offsetHeight || 0;
  
    // Prevent tooltip from overflowing right side
    if (newX + tooltipWidth > viewportWidth) {
      newX = event.clientX - tooltipWidth - offset;
    }
  
    // Prevent tooltip from overflowing bottom side
    if (newY + tooltipHeight > viewportHeight) {
      newY = event.clientY - tooltipHeight - offset;
    }
  
    tooltipX.value = newX;
    tooltipY.value = newY;
  };
  </script>
  