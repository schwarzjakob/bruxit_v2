<template>
    <el-row justify="center" style="margin-bottom: 100px;">
        <h1>Sensor Data Labeling and Analysis Tool</h1>
    </el-row>
    <el-row justify="center" style="margin-bottom: 100px;">
        <el-col :span="10">
            <PipelineStepper :step="4" />
        </el-col>
    </el-row>

    <!--DIALOG-->
    <el-dialog
        v-model="showDialog"
        width="500"
    >
        <h1>Welcome to the Sensor Data Labeling and Analysis Tool!</h1>
        <p>This tool....</p>
        <p><b>Before starting please save your desired settings clicking on the top right settings button.</b></p>
    </el-dialog>



    <!--USER AVATARS-->
    <el-row justify="center">
        <div>
           <el-avatar class="avatar-button" :size="220" src="https://cdn-icons-png.freepik.com/512/13518/13518010.png?ga=GA1.1.840118240.1706697088" @click="handleClick('advanced')"/> 
           <br />
           <h2 style="margin-left: 55px ;">Advanced</h2>
        </div>
        <div>
            <el-avatar class="avatar-button" :size="220" src="https://cdn-icons-png.freepik.com/512/6645/6645221.png?ga=GA1.1.840118240.1706697088" @click="handleClick('basic')"/>
            <br />
            <h2 style="margin-left: 82px ;">Basic</h2>
        </div>

    </el-row>
</template>

<script>
import PipelineStepper from '../components/PipelineStepper.vue'
import { ElMessage } from 'element-plus';

export default{
    name: 'HomePage',
    components: {
        PipelineStepper,
    },
    data () {
        return {
            settingsSaved: false,
            showDialog: true
        }
    },
    async mounted(){
        await this.getSettingsSaved();
        this.$store.commit('setSettingsSaved', false);

    },
    methods: {
        handleClick(userType){
            if(this.settingsSaved){
                this.$store.commit('setUserType', userType);
                this.$router.push('/patient-data');
            } else {
                ElMessage({message: 'Define settings before starting!', type: 'warning'})
            }
        },
        async getSettingsSaved(){
            // TODO: Change checking if settings exist in DATABASE
            console.log(this.$store.state.settingsSaved)
            console.log(typeof this.$store.state.settingsSaved)
            this.settingsSaved = this.$store.state.settingsSaved;
            if(this.$store.state.settingsSaved){
                this.showDialog = false;
            }
        }
    }
}

</script>

<style>
.avatar-button {
  cursor: pointer;
  display: inline-block;
  transition: transform 0.2s ease;
  background-color: #66b1ff;
  margin-right: 50px;
  border:2px solid black;
}
.avatar-button:hover {
  transform: scale(1.05);
}
</style>