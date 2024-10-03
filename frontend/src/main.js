import 'element-plus/dist/index.css';
import { createApp } from 'vue';
import App from './App.vue';
import ElementPlus from 'element-plus';
import en from 'element-plus/dist/locale/en.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import store from './store'
import * as VueRouter from 'vue-router'
import PathNotFoundPage from './pages/PathNotFoundPage.vue'
import HomePage from './pages/HomePage.vue'
import SettingsPage from './pages/SettingsPage.vue'
import PatientDataPage from './pages/PatientDataPage.vue'
import SleepStageDetectionPage from './pages/SleepStageDetectionPage.vue'
import EventsClassificationPage from './pages/EventsClassificationPage.vue'
import MonitoringPage from './pages/MonitoringPage.vue'
import D3Example from './pages/D3Example.vue'
import DemoPage from './pages/DemoPage.vue'
import ECPage from './pages/ECPage.vue';
import ECPage2 from './pages/ECPage2.vue';
import EventsClassificationDef from './pages/EventsClassificationDef.vue';



const router = VueRouter.createRouter({
    history: VueRouter.createWebHistory(process.env.BASE_URL),
     routes:[{
        path: '/:pathMatch(.*)*',
        component: PathNotFoundPage
    }, {
         path: '/',
         component: HomePage,
     }, {
         path: '/ssd',
         component: SleepStageDetectionPage,
     }, {
         path: '/monitoring',
         component: MonitoringPage,
     },{
         path: '/events-classification',
         component: EventsClassificationPage,
     },{
        path: '/patient-data',
        component: PatientDataPage
    }, {
        path: '/settings',
        component: SettingsPage
    }, {
        path: '/d3-example',
        component: D3Example
    }, {
        path: '/demo',
        component: DemoPage
    },
    {
        path: '/ec',
        component: ECPage
    },
    {
        path: '/ec2',
        component: ECPage2
    },{
        path: '/ec-def',
        component: EventsClassificationDef
    },] 
 })

router.beforeEach(async (to, from, next) => {
await store.restored;
next();
});

export default router;

const app = createApp(App)
app.use(router)
app.use(ElementPlus, {
    locale: en,
})
app.use(store)
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}
app.mount('#app')
