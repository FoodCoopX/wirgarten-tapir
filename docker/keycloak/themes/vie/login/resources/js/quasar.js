/* 
  Define the Quasar app using UMD version
  see https://quasar.dev/start/umd/#quasar-config-object
*/ 

// Override locale
const appLocale = Quasar.lang.getLocale().substring(0, 2)
const kcLocale = Quasar.Cookies.get('KEYCLOAK_LOCALE')
if (appLocale !== kcLocale) {
  Quasar.Cookies.set('KEYCLOAK_LOCALE', appLocale)
  location.reload()
}

// Create the Vue app
const app = Vue.createApp({
  setup () {
    // Functions
    async function popup (title, file) {
     const content = await fetch(file)
      Quasar.Dialog.create({
        title,
        message: await content.text(),
        html: true,
        style: 'width: 800px; max-width: 90vw;',
        ok: {
          color: 'primary'
        }
      })
    }
    // Expose 
    return {
      email: Vue.ref(''),
      password: Vue.ref(''),  
      rememberMe: Vue.ref('off'),
      loginLoading: Vue.ref(false),
      resetPasswordLoading: Vue.ref(false),
      passwordNew: Vue.ref(''),
      passwordConfirm: Vue.ref(''),
      updatedPasswordLoading: Vue.ref(false),
      showPassword: Vue.ref(false),
      showPasswordNew: Vue.ref(false),
      showPasswordConfirm: Vue.ref(false),
      popup
    }
  }
})
// Tell Vue to use Quasar using the specified configuration
app.use(Quasar, {
  config
})
// Mount the Quasar app
app.mount('#q-app')


