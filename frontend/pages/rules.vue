<template>
    <main>
        <div v-if="loading">
        <Loading/>
    </div>

    <div v-if="!loading">
        <Navbar/>
    </div>
    </main>
</template>

<script setup lang="ts">
import {Navbar, Loading} from "#components"
const loading = ref<boolean>(false)


</script>