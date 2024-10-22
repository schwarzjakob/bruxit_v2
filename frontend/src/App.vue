<template>
  <el-row>
    <el-col :span="23">
      <HomeButton/>
    </el-col>
    <el-col :span="1">
      <SettingsButton/>
    </el-col>
    </el-row>
  <div class="page-wrap">
    <router-view></router-view>
  </div>

</template>

<script>
import HomeButton from './components/HomeButton.vue';
import SettingsButton from './components/SettingsButton.vue';
export default {
  name: 'App',
  components: {
    HomeButton,
    SettingsButton
  },
}
</script>

<style>
/* Apply Sans-serif font globally to all text elements */
* {
  font-family: 'Sans-serif', Arial, Helvetica, sans-serif;
}
</style>