<script setup lang="ts">
import { useRoute } from "vue-router";


const routes = [
    { path: "/leaderboard", name: "Leaderboard" },
    { path: "/rules", name: "Rules" },
    { path: "/admin", name: "Admin" },
]
</script>

<template>
    <nav
        class="bg-blurple rounded-full py-2 text-white p-4 flex gap-6 px-20 shadow-lg justify-center"
    >
        <NuxtLink
            to="/"
            class="hover:text-dc-gray transition-all duration-150"
            :class="{ 'font-bold border-b-2 border-white': $route.path === '/' }"
        >
            Home
        </NuxtLink>
        <NuxtLink
            v-for="route in routes"
            :key="route.path"
            :to="route.path"
            class="hover:text-dc-gray transition-all duration-150"
            :class="{
                'font-bold border-b-2 border-white': $route.path === route.path,
            }"
        >
            {{ route.name.charAt(0).toUpperCase() + route.name.slice(1) }}
        </NuxtLink>
    </nav>
</template>
