<template>
    <router-link :to="'/settings/'">
        <el-button circle>
            <el-icon :size="20"><Setting /></el-icon>
        </el-button>
    </router-link>   
</template>

<script>
export default {
    name: "SettingsButton",
}
</script>