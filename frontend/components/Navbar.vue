<script setup lang="ts">

const routes = [
    { path: "/leaderboard", name: "Leaderboard" },
    { path: "/rules", name: "Rules" },
    { path: "/admin", name: "Admin" },
]

</script>

<template>
    <nav
        class="bg-dc-accent fixed top-0 left-0 w-full text-white p-4 flex gap-6 shadow-lg justify-center z-50"
    >
        <NuxtLink
            to="/"
            class="hover:text-blurple transition-all duration-150"
            :class="{ 'font-bold border-b-2 border-blurple': $route.path === '/' }"
        >
            Home
        </NuxtLink>
        <NuxtLink
            v-for="route in routes"
            :key="route.path"
            :to="route.path"
            class="hover:text-blurple transition-all duration-150"
            :class="{
                'font-bold border-b-2 border-white': $route.path === route.path,
            }"
        >
            {{ route.name.charAt(0).toUpperCase() + route.name.slice(1) }}
        </NuxtLink>
    </nav>
    <div class="py-10"></div>
</template>
