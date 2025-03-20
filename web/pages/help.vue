<template>
    <main class="flex flex-col justify-center items-center p-20 gap-8 select-none">
        <div>
            <Navbar />
        </div>
        <table v-for="(tab, index) in helpRows" :key="index" class="bg-dc-accent rounded-xl w-full">
            <thead>
                <tr>
                    <th class="p-4 text-center text-blurple font-sans text-2xl">{{ tab.title }}</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td v-if="!tab.channel_link" class="p-4 text-center font-sans text-green-500 text-lg"
                    >{{ tab.first_line }}</td>
                    <td v-else class="p-4 text-center font-sans text-green-500 text-lg cursor-pointer"
                    @click="channelRedirect(tab.channel_link)"
                    >{{ tab.first_line }}</td>
                </tr>
                <tr>
                    <td class="p-4 text-center font-sans px-20">{{ tab.text }}</td>
                </tr>
                <tr v-if="tab.img_url">
                    <td class="flex justify-center items-center w-full p-6">
                        <img :src="tab.img_url" alt="Image" class="border-2 border-blurple rounded-lg max-w-[80%] h-auto overflow-hidden">
                    </td>
                </tr>
                <tr v-if="tab.footer">
                    <td class="text-blurple text-center pb-4 underline">
                        {{ tab.footer }}
                    </td>
                </tr>
            </tbody>
        </table>
    </main>
</template>

<script setup lang="ts">
import { Navbar } from '#components';

const channelRedirect = ((url: string) => {
    window.open(url)
}) 


const helpRows = [
    {
        title: "Submitting Items",
        first_line: "/submit [item] [attachment]",
        text: "Submits an item to the event, make sure to use the autofill feature of the command to register the item properly. Once submitted the item gets listed for approval, this is handled by the opposing clan's selected event staff to prevent foul play. If for some reason this does not work, ask one of your clan's event staff to submit in your stead using their admin command.",
        footer: "Note: Screenshots require, Visible RSN, Drop in chatbox if applicable, Event Codeword Visible",
        img_url: "https://placehold.co/600x400.png"
    },
    {
        title: "Setting Start & End [ KC/POINTS/OTHER ]",
        first_line: "/set [ start | end ] [ activity ] [ amount ] [ attachment ]",
        text: "Set start & end count for activities who cannot be easily tracked via tools like WOM. (Ex. Herbiboar KC, Giant Keys, Clue Caskets) permissible screenshots include (Collection Log, Chat Command, NPC Chatbox)",
        footer: "Note: Requires Visible RSN & Event Code in screenshot.",
        img_url: "https://placehold.co/600x400.png"
    },
    {
        title: "Questions Regarding Event",
        first_line: "Click me to redirect to Q&A",
        text: "Keep any questions that are relevant in this channel, if something is asked we'd like to answer publicly so the question isn't asked repeatedly.",
        channel_link: "https://discord.com/channels/1343212912281653250/1343212913476767837"
    },
    {
        title: "Errors with Bot & Website",
        first_line: "Reach out to Salt (Idkbruh Ingame) from Iron Foundry",
        text: "Please grab a screenshot of any errors and double check you aren't doing something wrong before reaching out!"
    },
    {
        title: "Staff & Event Helpers",
        first_line: "Run: /help Admin for a list of commands you have access to.",
        text:"The one you might have to use at some point is: /admin submit [ @user ] [ item ] [ attachment ] This submits the item as if the person who received the drop ran the normal command, this is just a backup in case something isn't working for any individuals.",
        img_url: "https://placehold.co/600x400.png"
    }
];
</script>