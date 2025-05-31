// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss', '@nuxt/icon'],
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      port: 80,
      host: "0.0.0.0"
    }
  },
  app: {
    head: {
      title: "Ironclad vs Ironfoundry",
      link: [
        {
          rel: 'icon',
          type: 'image/x-icon',
          href: '/ironfoundry.ico'
        }
      ],
      meta: [
            { property: 'og:title', content: 'Clad vs Foundry' },
            { property: 'og:description', content: 'Frenzy Tracker' },
            { property: 'og:image', content: 'https://ironfoundry.cc/frenzyvs.png' },
            { property: 'og:url', content: 'https://ironfoundry.cc' },
            { property: 'og:type', content: 'website' },
            {property: 'twitter:card', content: 'summary_large_image'}
          ],
    }
  }
});
