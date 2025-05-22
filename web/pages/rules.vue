<template>
  <main
    class="flex flex-col justify-center items-center p-20 gap-8 select-none"
  >
    <div>
      <div>
        <Navbar />
        <Refresh class="z-50" />
      </div>
        <div class="min-h-screen flex flex-col items-center p-4">
          <!-- Title Section -->
          <h1 class="text-3xl font-semibold text-center mb-6">Frenzy Rules</h1>

          <!-- Rules List -->
          <div class="bg-dc-accent p-6 rounded-lg shadow-lg w-full max-w-3xl">
            <ul class="space-y-4">
              <li
                v-for="(rule, index) in rules"
                :key="index"
                class="flex items-start space-x-6 space-y-6 py-2 border-b border-dc-bg"
              >
                <span class="font-semibold text-xl px-2 text-gray-500">{{
                  index + 1
                }}</span>
                <p class="text-blurple text-lg">{{ rule }}</p>
              </li>
            </ul>
          </div>
        </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { Navbar, Refresh } from "#components";

const rules = [
  "One account per person that has to be in the appropriate clan for the duration of the event.",
  "Screenshots for tile completion must be submitted with the event password using the Runelite plugin “Clan Events” or “wiseoldman”. Mobile users must type the password in the chat box. Password to be released at event start time.",
  "No use of the GE will be permitted for buying items to complete tiles. (Ex. Implings, Larran's Keys, etc ...)",
  "Items must be drops and not purchased (Ex. Obsidian shield cannot be bought with Tokkul)",
  "From scratch items do not need to be completed by a single person. (Ex. Kodai Wand could have one person get the Insignia and another get the MTA points).",
  "Items bought with points do not actually need to be purchased, just show starting and ending points that they have been gained.",
  "Only individuals who received the drop can submit the drop (cannot submit for a teammate)",
  "We want a clean competition, friendly banter is encouraged however don’t be a dick, if you go overboard and cross any lines you can be subject for removal from the event.",
  "You must be in your respective clans the whole event, with Clanchat ON."
];
</script>
