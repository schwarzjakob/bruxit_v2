<template>
    <el-tag :type="userTypeTagType" size="large">
        <div v-if="userType === 'advanced'">
            Editor
        </div>
        <div v-else>
            Viewer
        </div>
    </el-tag>
</template>
  

<script>
    export default {
        name: "UserTag",
        data () {
            return {
                userType: '',
                userTypeTagType: ""
            }
        },
        async mounted()  {
            await this.getUserType();
        },
        methods: {
            async getUserType(){
                this.userType = this.$store.state.userType;

                if(this.$store.state.userType === "advanced"){
                    this.userTypeTagType = "success"
                } 
                if(this.$store.state.userType === "basic"){
                    this.userTypeTagType = "warning"
                }
            },
        }
    }
</script>
