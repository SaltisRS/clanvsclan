<template>
    <div class="fixed top-2 right-2 justify-center px-4 text-xl"
    >
    {{ points + " Points"}}
    </div>
</template>


<script setup lang="ts">
    defineProps<{points: number}>()
</script>