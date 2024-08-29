<template>
<h1>Settings Page</h1>
<el-button @click="saveSettings">
    Save
</el-button>
</template>

<script>
export default{
    name: "SettingsPage",
    methods: {
        saveSettings(){
            this.$store.commit('setSettingsSaved', true);
        }
    }
}
</script>