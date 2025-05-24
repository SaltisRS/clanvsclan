<script setup lang="ts">

const routes = [
    { path: "/leaderboard", name: "Leaderboard" },
    { path: "/rules", name: "Rules" },
    {path: "/help", name: "Help"}
]

const redirectToWiseOldMan = () => {
  window.open("https://wiseoldman.net/competitions/90513", "_blank");
};

</script>

<template>
    <nav
        class="bg-dc-accent fixed top-0 left-0 w-full text-white p-4 flex gap-6 shadow-lg justify-center z-50 border-b border-gray-500"
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
                'font-bold border-b-2 border-blurple': $route.path === route.path,
            }"
        >
            {{ route.name.charAt(0).toUpperCase() + route.name.slice(1) }}
        </NuxtLink>
    </nav>
    <div class="fixed z-50 top-12 right-0 size-24 opacity-25 cursor-pointer hover:brightness-110 hover:opacity-100 rotate-12 transition-all duration-150">
        <img src="public/wom.png" alt="Wiseoldman Competition"
        @click="redirectToWiseOldMan"
        >
    </div>
</template>
