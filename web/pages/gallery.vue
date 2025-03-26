<template>
  <main class="min-h-screen flex flex-col justify-center items-center bg-dc-bg overflow-hidden">
    <div>
      <Navbar />
      <Refresh class="z-50" />
    </div>

    <div class="w-full space-y-6">
      <div 
        v-for="(row, rowIndex) in galleryRows" 
        :key="'row-' + rowIndex"
        class="relative w-full overflow-hidden"
      >
        <div
          class="flex gap-2 py-2"
          :class="rowIndex % 2 === 0 ? 'animate-scroll' : 'animate-scroll-reverse'"
        >
          <div 
            v-for="(image, imageIndex) in shuffledRows[rowIndex]" 
            :key="'image-' + imageIndex"
            class="slide relative"
            @click="openLightbox(image.image)"
          >
            <img 
              :src="image.image" 
              class="rounded-lg border border-dc-accent w-48 h-32 object-cover cursor-pointer overflow-hidden"
            />
            <div v-if="getClanImage(image.clan)" class="absolute rounded-full top-2 left-2 size-6 opacity-60">
              <img :src="getClanImage(image.clan)"/>
            </div>
          </div>
        </div>
      </div>
    </div>
  
      <!-- Lightbox -->
      <div 
        v-if="lightboxImage" 
        class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-90 transition-opacity duration-300 z-50 overflow-hidden"
        @click="closeLightbox"
      >
        <img :src="lightboxImage" class="rounded-xl border-4 border-dc-accent overflow-hidden">
      </div>
    </main>
  </template>
  

<script setup lang="ts"> 
import { ref} from "vue";
const slides = ref<any[]>([]);
const shuffledRows = ref<any[]>([]);
const galleryRows = Array.from({ length: 7 });
const lightboxImage = ref<string | null>(null);

function shuffleArray(arr: any[]) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

const getClanImage = (clan: "Iron Foundry" | "Ironclad") => {
  const clanImages = {
    "Iron Foundry": "/ironfoundry.png",
    "Ironclad": "/ironclad.png",
  };
  return clanImages[clan] || "/ironfoundry.png";
};


onMounted(async () => {
  try {
    const response = await fetch("https://cvc-backend:8001/gallery");
    const data = await response.json();
    
    if (Array.isArray(data)) {
      slides.value = data;
      
      // Shuffle rows
      const rows = galleryRows.map(() => {
        const shuffled = [...slides.value];
        shuffleArray(shuffled);
        return shuffled;
      });
  
      // Ensure each row has enough slides to fill the screen without gaps
      shuffledRows.value = rows.map((row) => {
        const requiredSlides = Math.ceil(window.innerWidth); // Adjust based on slide width
        const repeatedSlides = [...row];

        // Keep appending the images until we fill the screen width
        while (repeatedSlides.length < requiredSlides * 2) {  // Double to ensure the loop works seamlessly
          repeatedSlides.push(...row);
        }

        // Slice to avoid overflow and maintain exact size
        return repeatedSlides.slice(0, requiredSlides);
      });
    }
  } catch (error) {
    console.error('Error fetching gallery data:', error);
  }
});

const openLightbox = (image: string) => {
  lightboxImage.value = image;
};

const closeLightbox = () => {
  lightboxImage.value = null;
};
</script>

<style>
@keyframes scroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-100%);
  }
}

@keyframes scroll-reverse {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(0);
  }
}

.animate-scroll {
  display: flex;
  white-space: nowrap;
  animation: scroll 30s linear infinite;
  width: 100%;
}

.animate-scroll-reverse {
  display: flex;
  white-space: nowrap;
  animation: scroll-reverse 30s linear infinite;
  width: 100%;
}

.slide {
flex-shrink: 0;
  width: auto;
  height: auto;
}


</style>
