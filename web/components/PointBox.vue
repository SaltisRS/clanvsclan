<template>
    <div class="fixed top-3 right-2 justify-center px-10 text-xl border-b-2 border-t-2 border border-blurple rounded-full bg-dc-bg"
    >
    {{ points + " Points"}}
    </div>
</template>


<script setup lang="ts">
    defineProps<{points: number}>()
</script>