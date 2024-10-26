<template>
    <el-row style="margin-top: 10px;">
        <el-col :span="2"><router-link :to="'/patient-data/'"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Patient Data</el-button></router-link></el-col>
        <el-col :span="1" :offset="2"><UserTag /></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="1" /></el-col>
        <el-col :span="2" :offset="1"><router-link :to="'/monitoring/'"><el-button type="primary"> Download Events  <el-icon> <ArrowRight /> </el-icon></el-button></router-link></el-col>
    </el-row>
    <!--
    <el-row justify="center">
        <h2 class="page-title">
            Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB
        </h2>
    </el-row>
-->
    <el-row justify="center">
        <h2 style="color: #409EFF">
            <el-icon><User /></el-icon> Patient {{ this.$store.state.patientId }}
            <el-icon style="margin-left:5px"><Calendar /></el-icon> Week {{ this.$store.state.weekId }}
            <el-icon style="margin-left:5px"><Document /></el-icon> File {{ this.$store.state.file }}
            <el-icon style="margin-left:5px"><Files /></el-icon> Size {{ this.$store.state.fileSize }} GB
        </h2>
    </el-row>
    <!--BASIC USER-->
    <div v-if="this.$store.state.userType==='basic'">
        <el-row justify="center">
            <el-col :span="7">
                <div style="display: flex; align-items: center;">
                    <el-select v-model="selectedImageLabel" placeholder="Select an image" @change="updateImage">
                        <el-option
                            v-for="image in images"
                            :key="image.label"
                            :label="image.label"
                            :value="image.label"
                        />
                    </el-select>
                </div>
            </el-col>
        </el-row>
        <el-row justify="center">
            <!-- Display the selected image -->
            <div v-if="selectedImage">
                <el-image id="selected-image" :src="selectedImage" :alt="selectedImage" style="width: auto; height: 600px"
                    :zoom-rate="1.2" :max-scale="7" :min-scale="0.2" :preview-src-list="[selectedImage]"/>
            </div>
        </el-row>
    </div>

    <!--ADVANCED USER -->
    <div v-else>
        <el-row>
            <el-col :span="11" :offset="2" v-loading="imgLoading" element-loading-text="Loading night images..." class="centered-column">
                <!-- Select dropdown for image selection -->
                <div class="image-selection">
                    <el-select v-model="selectedImageLabel" placeholder="Select an image" @change="updateImage" style="width:300px;">
                        <el-option
                            v-for="image in images"
                            :key="image.label"
                            :label="image.label"
                            :value="image.label"
                        />
                    </el-select>
                    <el-button @click="this.loadImages('new')" style="margin-left: 8px;" :disabled="true">
                        Update
                    </el-button>
                </div>

                <!-- Display the selected image -->
                <div v-if="selectedImage" class="selected-image-container">
                    <el-image :src="selectedImage" :alt="selectedImage" style="width: auto; height: 240px"
                            :zoom-rate="1.2" :max-scale="7" :min-scale="0.2" :preview-src-list="[selectedImage]" />
                </div>
            </el-col>

            <el-col :span="11" class="centered-column">
                <el-radio-group v-model="heatMapRadio" @change="selectHeatMap(heatMapRadio)" :disabled="!ssdDataReceived || imgLoading">
                    <el-radio-button label="Events" value="events" />
                    <el-radio-button label="Sleep Stages" value="ssd" />
                </el-radio-group>
                <!--
                <div v-if="Object.keys(this.predictions).length === 0">
                    <h3>No events predicted.</h3>
                </div>
            -->
                <div v-if="heatMapRadio === 'events'" id="ec-heatmap" v-loading="(!ssdDataReceived) || imgLoading" element-loading-text="Retrieving events and sleep stages data..."></div>

                <div v-else id="ssd-heatmap" v-loading="(!ssdDataReceived) || imgLoading" element-loading-text="Retrieving sleep stages data..."></div>
            </el-col>
        </el-row>

        <el-row>
            <el-col :span="6" v-loading="!emgReceived || imgLoading">
                <el-tooltip
                    class="box-item"
                    effect="dark"
                    content="Not implemented yet."
                    placement="top"
                >
                    <el-button type="primary" style="width:100%; margin-top:3px"><el-icon style="margin-right: 3px"><Refresh /></el-icon> Retrain Model</el-button>
                </el-tooltip>
                <el-card>
                    <div v-if="amountEvents === 0">
                        <h3>No events predicted during currently selected frame.</h3>
                    </div>
                    <div v-else>
                        <h3>Predicted events:</h3>
                        <el-scrollbar height="560px">
                        <el-card
                            class="text item"
                            v-for="(value, key) in current5minEvents"
                            :key="key"
                            @click="clickCard()"
                        >
                            <!-- STATUS + ZOOM BUTTON -->
                            <i :style="{color: getEventStatus(eventStatus[key]).color}">{{ getEventStatus(eventStatus[key]).text }}</i>
                            <el-row justify="space-between" style="margin-bottom: 10px; margin-top:5px">
                            <el-button type="primary" round @click="zoomToEvent(key, value)" size="medium">
                                <el-tooltip content="Click to zoom" placement="top">
                                Event {{ key.slice(1) }}
                                </el-tooltip>
                            </el-button>
                            <!-- Popover Metrics -->
                            <el-popover
                                placement="top-start"
                                :width="200"
                                trigger="hover"
                            >
                                <h3><b>Event {{key.slice(1)}}</b></h3>
                                <b>EMG Metrics</b><br />
                                <i>(Values range from 0 to 100, averaged over event duration)</i><br>
                                <u>MR</u><br>
                                SD: {{ value.std_mr.toFixed(2) }}<br>
                                Fmean: {{ value.mnf_mr.toFixed(2) }}<br>
                                RMS: {{ value.rms_mr.toFixed(2) }}<br />
                                <u>ML</u><br>
                                SD: {{ value.rms_ml.toFixed(2) }}<br>
                                Fmean: {{ value.mnf_ml.toFixed(2) }}<br>
                                RMS: {{ value.rms_ml.toFixed(2) }}<br />
                                <b>HRV Metrics</b><br />
                                LF/HF: {{ value.HRV_lf_hf.toFixed(2) }}<br />   
                                Mean: {{ value.HRV_mean.toFixed(2) }}<br />
                                SD: {{ value.HRV_sdnn.toFixed(2) }}<br />
                                <template #reference>
                                <el-icon size="large" color="#409EFF"><InfoFilled /></el-icon>
                                </template>
                            </el-popover>
                            </el-row>

                            <!-- START/END TIMES + EVENT DETAILS -->
                            <div style="margin-left: 10px;">
                            <el-row justify="space-between">
                                <!-- Start & End times -->
                                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                                    <span><b>Start (s):</b></span>
                                    <el-input-number
                                        v-model="value.start_s"
                                        :precision="2"
                                        :step="0.5"
                                        :min="Math.min(...emgTime)"
                                        :max="value.end_s - 1"
                                        size="small"
                                        @change="updateMarkArea(key, value)"
                                        style="width: 120px; margin-left: 10px;"
                                    />
                                </div>
                                <div style="display: flex; align-items: center;">
                                    <span><b>End (s):</b></span>
                                    <el-input-number
                                        v-model="value.end_s"
                                        :precision="2"
                                        :step="0.5"
                                        :min="value.start_s + 1"
                                        :max="Math.max(...emgTime)"
                                        size="small"
                                        @change="updateMarkArea(key, value)"
                                        style="width: 120px; margin-left: 10px;"
                                    />
                                </div>
                                <div>
                                <b>Duration:</b> {{ (value.end_s - value.start_s).toFixed(2) }} s
                                </div>
                            </el-row>

                            <!-- SD and Duration -->
                            <el-row justify="space-between" style="margin-top: 10px;">
                                <div>
                                <b>SD:</b> {{ value.HRV_sdnn.toFixed(2) }}
                                </div>
                            </el-row>

                            <!-- EVENT TYPE + SENSOR SELECTION -->
                            <el-row justify="space-between" style="margin-top: 10px">
                                <div style="display: flex; align-items: center;  margin-bottom: 10px">
                                <b>Event Type:</b>
                                <el-radio-group
                                    v-model="eventTypes[key]"
                                    size="small"
                                    @change="updateEventType(key, eventTypes[key])"
                                    style="margin-left: 10px;"
                                >
                                    <el-radio-button label="Phasic" value="phasic" />
                                    <el-radio-button label="Tonic" value="tonic" />
                                    <el-radio-button label="Mixed" value="mixed" />
                                </el-radio-group>
                                </div>
                                <div style="display: flex; align-items: center;">
                                <b>Sensors:</b>
                                <el-checkbox-group
                                    v-model="sensorsCheckBox[key]"
                                    size="small"
                                    @change="handleSensorsCheckBoxChange(key, sensorsCheckBox[key], value)"
                                    style="margin-left: 10px;"
                                >
                                    <el-checkbox-button value="MR">MR</el-checkbox-button>
                                    <el-checkbox-button value="ML">ML</el-checkbox-button>
                                </el-checkbox-group>
                                </div>
                            </el-row>

                            <!-- REASON FOR DECISION -->
                            <el-row style="margin-top: 10px;">
                                <div>
                                <p><b>Reason for decision:</b></p>
                                <div v-if="!eventJustifications[key].saved">
                                    <el-input
                                        v-model="eventJustifications[key].justification"
                                        type="textarea"
                                        placeholder="Enter reason for accepting/discarding this event"
                                        rows="2"
                                        style="width: 100%;"
                                        :maxlength="200"
                                        show-word-limit
                                    />
                                    <p v-if="eventJustifications[key].justification.length > 200" style="color: red;">
                                        Character limit exceeded! Maximum 200 characters allowed.
                                    </p>
                                    <el-button 
                                        type="primary"
                                        :disabled="eventJustifications[key].justification.length > 200 || eventJustifications[key].justification.length === 0"
                                        @click="saveJustification(key, eventJustifications[key])"
                                        size="small"
                                        style="margin-top: 5px;">
                                        Save Reason
                                    </el-button>
                                </div>
                                <div v-else style="display: flex; align-items: center;">
                                    <p>{{ eventJustifications[key].justification }}</p>
                                    <el-button type="text" size="small" @click="editJustification(key)">
                                    <el-icon><Edit /></el-icon>
                                    </el-button>
                                </div>
                                </div>
                            </el-row>

                            <!-- CONFIRM / DISCARD EVENT -->
                            <el-row justify="center" style="margin-top: 10px;">
                                <el-radio-group
                                v-model="confirmedEvents[key]"
                                size="medium"
                                @change="updateConfirmedEvents(key, confirmedEvents[key], value)"
                                :fill="getFillColor(confirmedEvents[key])"
                                >
                                <el-radio-button label="Discard" :value="false" />
                                <el-radio-button label="Confirm" :value="true" />
                                </el-radio-group>
                            </el-row>
                            </div>
                        </el-card>
                        </el-scrollbar>
                    </div>
                    </el-card>

            </el-col> 
            <el-col :span="1" :offset="1" style="margin-top:300px">
                <el-button type="primary" circle @click="moveBackward()" :disabled="tileIndex==='0.00'"><el-icon><ArrowLeft /></el-icon></el-button>
            </el-col>
            <el-col :span="14" v-loading="!emgReceived || imgLoading" element-loading-text="Loading the data...">
                <el-row>
                        <div>
                            <p style="font-size: small;"><b>Thresholds (% of MVC)</b></p>
                            <label :span="2" style="font-size: small; margin-right: 10px"><b>MR:</b></label>
                            <el-input-number type="number" v-model="thresholdMr" :span="5" size="small" :step="1" @change="updateThresholdMr(thresholdMr)" style="margin-right: 10px; width:120px"/>
                            <label :span="2" style="font-size: small;margin-right: 10px;"><b>ML:</b></label>
                            <el-input-number type="number" v-model="thresholdMl" :span="5"  size="small" :step="1" @change="updateThresholdMl(thresholdMl)" style="margin-right: 10px; width:120px"/>
                        </div>
                        <div style="margin-left: 30px">
                            <el-button :plain="true" :type="editButtonType" size="small" @click="triggerEditMode()" style="margin-top:43px">
                                <el-icon style="margin-right: 5px"><Plus /></el-icon> Add event
                            </el-button>
                        </div>
                        <div v-if="selectionActive && startSelection && endSelection" style="margin-left: 30px">
                            <el-popover
                                placement="bottom"
                                :width="300"
                                trigger="click"
                                content="this is content, this is content, this is content"
                            >
                            <b>Add event</b>
                            <el-form :model="eventForm" class="form-container">
                                <el-form-item label="Start (s)">
                                <el-input-number v-model="eventForm.start" :precision="2" :min="0" label="Start Time" />
                                </el-form-item>
                                <el-form-item label="End (s)">
                                <el-input-number v-model="eventForm.end" :precision="2" :min="0" label="End Time" />
                                </el-form-item>
                                <b>Duration: {{ (eventForm.end - eventForm.start).toFixed(2)}} s</b>
                                <el-form-item label="Event type">
                                    <el-radio-group
                                    v-model="eventForm.eventTypeNewEvent"
                                    size="small"
                                >
                                    <el-radio-button label="Phasic" value="phasic" />
                                    <el-radio-button label="Tonic" value="tonic" />
                                    <el-radio-button label="Mixed" value="mixed" />
                                </el-radio-group>
                                </el-form-item>
                                <el-form-item label="Sensors">
                                    <el-checkbox-group
                                        v-model="eventForm.sensorsNewEvent"
                                        size="small"
                                    >
                                        <el-checkbox-button value="MR">MR</el-checkbox-button>
                                        <el-checkbox-button value="ML">ML</el-checkbox-button>
                                    </el-checkbox-group>
                                </el-form-item>
                                <el-form-item label="Reason for event">
                                    <el-input
                                        v-model="eventForm.justificationNewEvent"
                                        style="width: 240px"
                                        :rows="2"
                                        type="textarea"
                                        placeholder="Please input"
                                    />
                                </el-form-item>
                                <el-form-item style="margin-top: 5px;">
                                <el-button type="primary" @click="addNewEvent(eventForm)">Submit</el-button>
                                </el-form-item>
                            </el-form>
                                <template #reference>
                                <el-badge is-dot class="item" style="margin-top:43px">
                                    <el-button class="m-2" size="small" @click="updateSelectionValues">Save </el-button> 
                                </el-badge>
                                </template>
                            </el-popover>
                        </div>
                        <div style="margin-left: 30px">
                            <!--
                            <el-button id="zoom-button" :plain="true" :disabled="zoomDisabled" @click="activateZoom()">
                                Zoom
                            </el-button>
                        -->
                            <el-button id="zoom-button" :plain="true" size="small" :type="zoomButtonType" :disabled="selectionActive" @click="activateZoom()" style="margin-top:43px">
                                <el-icon style="margin-right:5px"><ZoomIn /></el-icon> Zoom
                            </el-button>
                            <!--
                            <el-button @click="zoomReset()" :disabled="!zoomActive">Zoom reset</el-button>
                        -->  
                            <el-button @click="zoomReset()" size="small" style="margin-top:43px">
                                <el-icon style="margin-right: 5px"><ZoomOut /></el-icon> Zoom reset</el-button>   
                        </div>
                    
                </el-row>
                
                <div id="emg-chart" style="width: 100%; height: 600px;"></div>
            </el-col>
            <el-col :span="1" style="margin-top:300px">
                <el-button type="primary" circle @click="moveForward()" :disabled="(parseFloat(parseFloat(this.tileIndex)+0.5).toFixed(2)) > parseFloat((parseFloat(totalCells)).toFixed(2))"><el-icon><ArrowRight /></el-icon></el-button>
            </el-col>
            
        </el-row>
    </div>

  </template>
  
  <script>
  import PipelineStepper from '../components/PipelineStepper.vue'
  import * as echarts from 'echarts';
  import { markRaw } from 'vue';
  import axios from 'axios';
  import {ArrowRight, ArrowLeft, Refresh, ZoomIn, ZoomOut, Plus, Calendar, User, Document, Files} from '@element-plus/icons-vue'
  import {reactive} from 'vue';
  import UserTag from '@/components/UserTag.vue';

  export default {
    name: 'EventsClassificationDef',
    components: {
        PipelineStepper,
        ArrowRight,
        ArrowLeft,
        UserTag,
        Refresh,
        ZoomIn,
        ZoomOut,
        Plus, 
        User, 
        Calendar,
        Document, 
        Files
    },
    async mounted(){
        if(this.$store.state.userType === 'advanced'){
            await this.getPredictions();
            await this.getThresholds();
            await this.getData((0).toPrecision(12));
            await this.getSsdData();

            if(this.heatMapRadio === 'events'){
                this.drawECHeatMap();
            }
            if (this.heatMapRadio === 'ssd') {
                await this.drawSSDHeatMap();
            }
        }
        this.loadImages("old");
    },
    data () {
        return {
            isImageVisible: true,
            mr: [],
            ml: [],
            stdMr: [], 
            stdMl: [],
            fMeanMr: [],
            fMeanMl: [],
            rri: [],
            hrvLfHf: [],
            hrvMean: [],
            hrvSdnn: [],
            emgTime: [],
            selectedInterval: [[0,0,0]],
            emgReceived: false,
            cancelToken: null,
            tileIndex: (0).toFixed(2),
            predictions: {},
            current5minEvents: {},
            amountEvents: 0,
            emgChart: null,
            confirmedEvents: {},
            emgDataLengthS: 0,
            eventTypes: {},
            eventJustifications: {},
            eventDurations: {},
            mvcMR: 0,
            mvcML: 0,
            maxAmplitudeMR: 0,
            maxAMplitudeML: 0,
            thresholdMr: 0,
            thresholdMl: 0,
            selectionActive: false,
            editButtonType: "",
            zoomButtonType: "",
            zoomDisabled: false,
            startSelection: null,
            endSelection: null,
            eventForm: reactive({
                start: 0,
                end: 0,
                justificationNewEvent: "",
                eventTypeNewEvent: "",
                sensorsNewEvent: ["MR", "ML"]
            }),
            sensorsCheckBox : {},
            eventStatus: {},
            totalCells: 0,
            images: [],
            selectedImage: '',
            selectedImageLabel: '',
            imgLoading: true,
            ssdData: [],
            ssdDataReceived: false,
            heatMapRadio: '',
            zoomActive: false,


        }
    },
    methods: {
        toggleImage() {
            this.isImageVisible = !this.isImageVisible;
        },
        async selectHeatMap(heatMapRadio){
            if(heatMapRadio === 'events'){
                this.drawECHeatMap();
            } if(heatMapRadio === 'ssd'){
                await this.drawSSDHeatMap();
            }
        },
        async saveJustification(key, value){
            console.log("patch on db")
            console.log(key, value)
            this.eventJustifications[key].saved = true;

            const path = `http://127.0.0.1:5000/justification/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;

            let payload= {'name': key, 'justification': value.justification};

            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.patch(path, payload, {headers})
                .then(() => {
                    console.log("Justification of prediction updated!")
                })
                .catch(err=>{
                    console.log(err)
                })
        },
        editJustification(key){
            this.eventJustifications[key].saved = false;
        },
        activateZoom() {
            this.zoomActive = !this.zoomActive;

            if(this.zoomActive){
                this.zoomButtonType = "primary"
            } else {
                this.zoomButtonType = ""
            }
            console.log("zoom active: ", this.zoomActive)
            this.emgChart.dispatchAction({
                type: 'takeGlobalCursor',
                key: 'dataZoomSelect',
                dataZoomSelectActive: this.zoomActive,
            });
        },
        zoomReset(){
            this.emgChart.dispatchAction({
                type: 'dataZoom',
                start: Math.min(...this.emgTime),
                end: Math.max(...this.emgTime)
            });

            // Deactivate zoom mode on double-click
            //this.emgChart.dispatchAction({
            //    type: 'takeGlobalCursor',
            //    key: 'dataZoomSelect',
            //    dataZoomSelectActive: false
            //});
        },
        async loadImages(version) {
            this.imgLoading = true
            const baseUrl = `http://localhost:5000/night-images/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}/${version}`;
            
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            // Make the request to get the image as a Blob
            await axios.get(baseUrl, {headers})
            .then(response => {
                // Create a URL for the image blob
                
                // Assign the blob URL to your image source or handle it as needed
                this.images = response.data;
                const wholeNightSignal = response.data.find(image => image.label === 'Whole Night Signal');
                console.log("WHOLE NIGHT SIGNAL: ", wholeNightSignal)
                if (wholeNightSignal) {
                    this.selectedImageLabel = wholeNightSignal.label;
                    this.selectedImage = `${wholeNightSignal.src}?t=${new Date().getTime()}`; // Append timestamp
                }
                this.imgLoading = false

                console.log("IMAGES: ", response.data)
            })
            .catch(err => {
                console.log(err);
            });
        },
        async getThresholds(){
            const path = `http://127.0.0.1:5000/patient-threshold/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    this.thresholdMr = res.data["MR"];
                    this.thresholdMl = res.data["ML"]

                })
                .catch(err=>{
                    console.log(err)
                })
        }, 
        updateImage(value) {
            const selectedImageData = this.images.find(image => image.label === value);
            const timestamp = new Date().getTime();

            if (selectedImageData) {
                this.selectedImage = `${selectedImageData.src}?t=${timestamp}`; // Append timestamp to the src
            }
        },
        getFillColor(confirmed) {
            // Green for Confirm, Red for Discard
            return confirmed ? '#13ce66' : '#ff4949';
        },
        triggerEditMode() {
            console.log("SELECTION MODE ACTIVE")
            this.selectionActive = !this.selectionActive;

            console.log(this.selectionActive)
            if(this.selectionActive){
                this.editButtonType = "primary"
                //this.zoomDisabled = true
            } else {
                this.editButtonType = ""
                //this.zoomDisabled = false
            }
            if(this.selectionActive===true){
                this.zoomActive = false;
                this.zoomButtonType = ""
                // Deactivate zoom mode on double-click
                this.emgChart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'dataZoomSelect',
                    dataZoomSelectActive: false
                });
                this.emgChart.dispatchAction({
                    type: 'takeGlobalCursor',
                    key: 'brush',
                    brushOption: {
                        brushType: 'lineX',
                        brushMode: 'single'
                    }
                });
            } else {
                console.log("ZOOOOOOOM: ", this.zoomActive)
                this.emgChart.dispatchAction({
                    type: 'brush',
                    areas: []
                });
            }
        },
        clickCard(){
            console.log("card clicked")
        },
        async updateEventType(key, value){
            const path = `http://127.0.0.1:5000/prediction-event-type/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;

            let payload= {};
            if (value ==''){
                this.eventTypes[key] = "";
            }
            payload['name'] = key;
            payload['event_type'] = value;

            console.log("PAYLOAD: ", payload)
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.patch(path, payload, {headers})
                .then(() => {
                    console.log("Event type of prediction updated!")
                    //updateMark areas?

                })
                .catch(err=>{
                    console.log(err)
                })

        },
        getEventStatus(eventStatus){
            let color = "black";
            if (eventStatus == "new"){
                color = "rgb(133.4, 206.2, 97.4)"
                return {'text': "Manually added", 'color': color }

            } else if (eventStatus == "model"){
                return {'text': "Predicted by model", 'color': color}

            } else if (eventStatus == "modified"){
                return {'text': "Edited", 'color': color}
            }
            return  {'text': "", 'color': color}

        },
        async handleSensorsCheckBoxChange(key, value, valueEvent){
            console.log("Change sensors on DB")
            console.log(key, value)
            if(value.length === 0){
                console.log("length: 0")
                this.sensorsCheckBox[key] = ['MR', 'ML']
            }

            const path = `http://127.0.0.1:5000/prediction-sensors/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;

            let payload= {};
            payload['name'] = key;
            payload['sensor'] = value;

            console.log("PAYLOAD: ", payload)
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.patch(path, payload, {headers})
                .then(() => {
                    console.log("Sensors of prediction updated!")
                    this.updateMarkArea(key, valueEvent)

                })
                .catch(err=>{
                    console.log(err)
                })

        },
        async reloadData(){
            await this.getPredictions();
            await this.getData(this.tileIndex);
            if(this.heatMapRadio === 'events'){
                this.drawECHeatMap();
            }
            if (this.heatMapRadio === 'ssd'){
                await this.drawSSDHeatMap();
            }
            
           
        }, 
        async addNewEvent(form){
            console.log("Add event: ", form.start, form.end)
            console.log(this.current5minEvents)
            //this.amountEvents ++;
            //this.current5minEvents[key] = value
            //await this.markEvent(this.eventForm.start, this.eventForm.end)
            const path = `http://127.0.0.1:5000/predict-events/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
            let payload= {};
            payload['start_s'] = form.start;
            payload['end_s'] = form.end;
            payload['event_type'] = form.eventTypeNewEvent;
            payload['sensor'] = form.sensorsNewEvent
            payload['justification'] = form.justificationNewEvent;
            console.log("PAYLOAD: ", payload)
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.post(path, payload, {headers})
                .then(() => {
                    console.log("Added new event!")
                    this.emgChart.dispatchAction({
                        type: 'brush',
                        areas: []
                    });
                    this.selectionActive = false;
                    this.editButtonType = ""
                    this.reloadData();

                    this.emgChart.dispatchAction({
                        type: 'takeGlobalCursor',
                        key: 'brush',
                        brushOption: false
                    });
                    

                })
                .catch(err=>{
                    console.log(err)
                })

        },
        updateSelectionValues(){
            this.eventForm.start = this.startSelection;
            this.eventForm.end = this.endSelection;
        },
        async updateConfirmedEvents(keyEvent, boolConfirmed, value){
            this.confirmedEvents[keyEvent] = boolConfirmed;
            const path = `http://127.0.0.1:5000/confirmed-events/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
            let payload= {};
            payload['name'] = keyEvent;
            payload['confirmed'] = boolConfirmed;
            payload['start_s'] = value.start_s;
            payload['end_s'] = value.end_s;
            console.log("PAYLOAD: ", payload)
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.patch(path, payload, {headers})
                .then(() => {
                    console.log("Confirmed events updated!")
                    this.updateMarkArea(keyEvent, value)
                    this.predictions[keyEvent].confirmed = boolConfirmed;
                    this.drawECHeatMap()

                })
                .catch(err=>{
                    console.log(err)
                })

        },
        updateMarkArea(key, value){
            console.log(value.start_s, value.end_s);
            console.log(this.confirmedEvents[key])
            if (this.emgChart) {
                const option = this.emgChart.getOption();
                console.log(option);
                
                // Check if there are any series in the chart options
                if (!option.series || option.series.length === 0) {
                    console.error('No series found in chart options');
                    return;
                }
                if(this.confirmedEvents[key] == true){
                    console.log("update confirm")
                    const path = `http://127.0.0.1:5000/confirmed-events/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
                    let payload= {};
                    payload['name'] = key;
                    payload['start_s'] = value.start_s;
                    payload['end_s'] = value.end_s;
                    payload['confirmed'] = this.confirmedEvents[key];
                    console.log("PAYLOAD: ", payload)
                    const headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    };
                    axios.patch(path, payload, {headers})
                        .then(() => {
                            console.log("Confirmed events start and end updated!")
                            this.eventStatus[key] = "modified"
                            this.zoomActive = false;
                            this.zoomButtonType = ""

                        })
                        .catch(err=>{
                            console.log(err)
                        })
                        
                        // Calculate the normalized start and end positions
                        let min = Math.min(...this.emgTime);
                        let max = Math.ceil(Math.max(...this.emgTime));
                        const start = parseFloat(value['start_s']); 
                        const end = parseFloat(value['end_s']); 
                        const startNorm = ((start - min) / (max - min)) * (300 - 0) + 0;
                        const endNorm = ((end - min) / (max - min)) * (300 - 0) + 0;

                        // First, remove any existing markArea entries for this key
                        option.series.forEach(series => {
                            if (series.markArea && series.markArea.data) {
                                series.markArea.data = series.markArea.data.filter(area => area[0].name !== key);
                            }
                        });

                        let found=false;
                        // Iterate through both series to update markArea
                        if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['MR', 'ML'].slice().sort())){
                            option.series.forEach(series => {
                                if (series.markArea && series.markArea.data) {
                                    // Update the corresponding markArea for the specified key
                                    series.markArea.data.forEach(area => {
                                        if (area[0].name === key) {
                                            found=true;
                                            area[0].xAxis = startNorm * 200; // Update the start xAxis
                                            area[1].xAxis = endNorm * 200; // Update the end xAxis
                                        }
                                    });
                                }
                            });
                        }
                        if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['MR'].slice().sort())){
                            option.series[0].markArea.data.forEach(area => {
                                if (area[0].name === key) {
                                    area[0].xAxis = startNorm * 200;
                                    area[1].xAxis = endNorm * 200;
                                }
                            });        
                        }
                        if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['ML'].slice().sort())){
                            option.series[1].markArea.data.forEach(area => {
                                if (area[0].name === key) {
                                    area[0].xAxis = startNorm * 200;
                                    area[1].xAxis = endNorm * 200;
                                }
                            });  
                        }


                        if (found === false) {
                            if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['MR', 'ML'].slice().sort())){
                                option.series.forEach(series => {
                                        series.markArea.data.push([
                                            { name: key, xAxis: startNorm * 200 }, // New start point
                                            { xAxis: endNorm * 200 } // New end point
                                    ]);
                                });
                            }
                            if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['MR'].slice().sort())){
                                option.series[0].markArea.data.push([
                                    { name: key, xAxis: startNorm * 200 }, // New start point
                                    { xAxis: endNorm * 200 }
                                ])        
                            }
                            if(JSON.stringify(this.sensorsCheckBox[key].slice().sort()) === JSON.stringify(['ML'].slice().sort())){
                                option.series[1].markArea.data.push([
                                    { name: key, xAxis: startNorm * 200 }, // New start point
                                    { xAxis: endNorm * 200 }
                                ])   
                            }
                        }

                
                } else {
                    option.series.forEach(series => {
                        if (series.markArea && series.markArea.data) {
                            // Remove the entry with area[0].name === key
                            series.markArea.data = series.markArea.data.filter(area => area[0].name !== key);
                        }
                    })
                }
                // Update the chart with the modified options
                this.emgChart.setOption(option, true); // true to not merge with the previous options
            }
        },
        async moveForward(){
            console.log("MOVE FORWARD")
            this.tileIndex = (parseFloat(this.tileIndex) + 0.50).toFixed(2)
            //console.log(this.tileIndex)
            
            console.log("length selected interval", this.selectedInterval.length)
            if(this.selectedInterval.length == 1){
                let xCurrent = this.selectedInterval[0][0]
                let yCurrent = this.selectedInterval[0][1]
                let value = this.selectedInterval[0][2]

                if (xCurrent == 17){
                    yCurrent = yCurrent +1
                    xCurrent = 0
                } else {
                    xCurrent = xCurrent + 1
                }
                this.selectedInterval.push([xCurrent, yCurrent, value])
            }
            else if(this.selectedInterval.length == 2){
                //this.selectedInterval.shift();
                console.log(this.selectedInterval)
                const maxArray = this.selectedInterval.reduce((max, current) => {
                // Primary condition: prioritize the array with a larger element at position 1
                    if (current[1] > max[1]) {
                        return current;
                    }
                    // Secondary condition: if position 1 is the same, pick the one with a larger element at position 0
                    if (current[1] === max[1] && current[0] > max[0]) {
                        return current;
                    }
                    return max;
                });
                this.selectedInterval = [maxArray];
            }
            if(this.heatMapRadio === 'events'){
                this.drawECHeatMap();
            }
            if (this.heatMapRadio === 'ssd'){
                await this.drawSSDHeatMap();
            }
            await this.getData(this.tileIndex);
        },
        async moveBackward(){
            console.log("move backward")
            this.tileIndex = (parseFloat(this.tileIndex) - 0.50).toFixed(2)
            console.log(this.tileIndex)
            let xCurrent = this.selectedInterval[0][0];
            let yCurrent = this.selectedInterval[0][1];
            let value = this.selectedInterval[0][2];


            if (this.selectedInterval.length == 1) {

                // Move backward in the grid
                if (xCurrent == 0) {
                    // If at the beginning of the row, move to the previous row
                    yCurrent = yCurrent - 1;
                    xCurrent = 17;  // Reset to the last column
                } else {
                    // Move one step back in the same row
                    xCurrent = xCurrent - 1;
                }

                // Update the selected interval with the new xCurrent, yCurrent
                this.selectedInterval.push([xCurrent, yCurrent, value]);

            } else if (this.selectedInterval.length == 2) {
                console.log("selectedInterval: ", this.selectedInterval)
                console.log(xCurrent, yCurrent, value)
                
                const minArray = this.selectedInterval.reduce((min, current) => {
                    // Always prioritize the array with a smaller element at position 1
                    if (current[1] < min[1]) {
                        return current;
                    }
                    // If no smaller element at position 1, check based on the smallest at position 0
                    if (current[1] === min[1] && current[0] < min[0]) {
                        return current;
                    }
                    return min;
                });
                this.selectedInterval = [minArray];
            }

            // Redraw the heatmap and fetch the new data
            if(this.heatMapRadio === 'events'){
                this.drawECHeatMap();
            }
            if (this.heatMapRadio === 'ssd'){
                await this.drawSSDHeatMap();
            }
            await this.getData(this.tileIndex);
        },
        async getData(idx) {
            this.emgReceived = false;
            this.amountEvents = 0;

            const mvcPath = `http://127.0.0.1:5000/mvc/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
            const ndPath = `http://127.0.0.1:5000/night-duration/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;

            const emgPath = `http://127.0.0.1:5000/get-emg/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}/${idx}`;
            const headers = {
                Accept: 'application/json',
                'Content-Type': 'application/json',
            };


            // Cancel the previous request if it exists
            if (this.cancelToken) {
                this.cancelToken.cancel('Previous request canceled due to new click.');
            }

            // Create a new cancel token for the new request
            this.cancelToken = axios.CancelToken.source();

            try {

                await axios.get(mvcPath, {headers})
                .then((res) => {
                    this.mvcMR = (res.data.mvc_mr).toFixed(2);
                    this.mvcML = (res.data.mvc_ml).toFixed(2);
                    console.log("mvcMR", res.data.mvc_mr)

                })
                .catch(err=>{
                    console.log(err)
                })
                await axios.get(ndPath, {headers})
                .then((res) => {
                    this.emgDataLengthS = res.data.duration_s;
                    console.log("duration s: ", res.data.duration_s)

                })
                .catch(err=>{
                    console.log(err)
                })

                const res = await axios.get(emgPath, {
                headers,
                cancelToken: this.cancelToken.token, // Attach the cancel token
                });

                console.log(res.data);
                this.mr = res.data.MR;
                this.ml = res.data.ML;
                this.stdMr = res.data.std_mr;
                this.rri = res.data.RRI;
                this.stdMl = res.data.std_ml;
                this.fMeanMr = res.data.mnf_mr;
                this.fMeanMl = res.data.mnf_ml;
                this.hrvLfHf = res.data.HRV_lf_hf;
                this.hrvMean = res.data.HRV_mean;
                this.hrvSdnn = res.data.HRV_sdnn;
                this.maxAmplitudeMR = Math.max(...res.data.MR);
                this.maxAmplitudeML = Math.max(...res.data.ML);
                console.log("max amplitude mr: ", this.maxAmplitudeMR)
                this.emgTime = res.data.EMG_t;
                this.emgReceived = true;

                console.log(Object.keys(this.predictions).length)

                if(Object.keys(this.predictions).length >0){
                    let events = this.mapEventTimesToEmgTimeInRange(this.predictions, res.data.EMG_t);
                    console.log(events)
                    console.log(Object.keys(events).length)
                    this.current5minEvents = events;
                    if(Object.keys(events).length >0){
                        this.amountEvents = Object.keys(events).length;
                        console.log("amount: ", this.amountEvents)
                    }
                    for (const key of Object.keys(events)){
                        console.log(key)
                        this.confirmedEvents[key] = events[key].confirmed;
                        this.eventTypes[key] = events[key].event_type;
                        let saved;
                        if(events[key].justification !== ''){
                            saved = true;
                        } else {
                            saved = false;
                        }
                        this.eventJustifications[key] = {'justification': events[key].justification, 'saved': saved};
                        this.eventDurations[key] = {}
                        this.eventStatus[key] = events[key].status;
                        if(events[key].sensor === 'both'){
                            this.sensorsCheckBox[key] = ['MR', 'ML']
                        } else if (events[key].sensor === 'MR') {
                            this.sensorsCheckBox[key] = ['MR']
                        } else if (events[key].sensor === 'ML'){
                            this.sensorsCheckBox[key] = ['ML']
                        }
                    }
                }
                
                this.drawEMGLinePlot(); // Function to draw the EMG plot with the fetched data
            } catch (error) {
                if (axios.isCancel(error)) {
                console.log('Previous request canceled:', error.message);
                } else {
                console.log(error);
                }
            }
        },
        mapEventTimesToEmgTimeInRange(events, emgTime) {
            const emgTimeMin = Math.min(...emgTime);
            const emgTimeMax = Math.max(...emgTime);

            console.log("min: ", emgTimeMin)
            console.log("max: ", emgTimeMax)
            //events = events.replace(/NaN/g, 'null');
            //events = JSON.parse(events)
            console.log(typeof events)

            // Helper function to find the closest value in the emgTime array
            function findClosest(time, emgTime) {
                return emgTime.reduce((prev, curr) => (Math.abs(curr - time) < Math.abs(prev - time) ? curr : prev));
            }

            // Map start_s and end_s to the closest values in emgTime only if within range
            const mappedEvents = Object.keys(events).reduce((mapped, eventKey) => {
                const event = events[eventKey];
                //console.log(event)
                // Only map if both start_s and end_s are within the emgTime range
                if (event.start_s >= emgTimeMin && event.end_s <= emgTimeMax) {
                const closestStart = findClosest(event.start_s, emgTime);
                const closestEnd = findClosest(event.end_s, emgTime);

                // Create a new object with mapped start_s and end_s
                mapped[eventKey] = {
                    ...event,
                    start_s: closestStart,
                    end_s: closestEnd,
                };
                }

                return mapped;
            }, {});

            return mappedEvents;
        },
        async getPredictions(){
            this.loading = true;
            const path = `http://127.0.0.1:5000/predict-events/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    this.predictions = res.data;
                    console.log("Predictions")
                    console.log(res.data)
                    if(Object.keys(res.data).length > 0){
                        this.heatMapRadio = "events"
                    } else {
                        this.heatMapRadio = "ssd"
                    }

                })
                .catch(err=>{
                    console.log(err)
                })
        },
        
        zoomToEvent(key, value){
            if (this.emgChart) {
                //this.basicStyle = {}
                let min = Math.min(...this.emgTime)
                let max = Math.ceil(Math.max(...this.emgTime))
                const start = parseFloat(value['start_s']);
                const end = parseFloat(value['end_s']);
                const startNorm = ((start - min) / (max-min)) * (300-0) + 0
                const endNorm = ((end - min) / (max-min)) * (300-0) + 0

                console.log(startNorm, endNorm)
                this.emgChart.dispatchAction({
                    type: 'dataZoom',
                    startValue: (startNorm*200) - (5*200),
                    endValue: (endNorm*200) + (5*200)
                });
            }
        },
        
        async drawEMGLinePlot(){
            let emgChart = markRaw(echarts.init(document.getElementById('emg-chart')));
            this.emgChart = emgChart;

            let mvcMR = this.mvcMR;
            let mvcML = this.mvcML;
            let stdMR = this.stdMr;
            let stdML = this.stdMl;
            let fMeanMr = this.fMeanMr;
            let fMeanMl = this.fMeanMl;
            let rri = this.rri;
            let hrvLfHf = this.hrvLfHf;
            let hrvMean = this.hrvMean;
            let hrvSdnn = this.hrvSdnn;
            //let markAreaData = [];
            let markAreaDataMR = [];
            let markAreaDataML = [];
            let events = {}

            if(Object.keys(this.predictions).length > 0) {
                events = this.mapEventTimesToEmgTimeInRange(this.predictions, this.emgTime);
                this.current5minEvents = events;
                console.log(this.predictions)
                console.log("events in 5 min: ", events)

                let min = Math.min(...this.emgTime)
                let max = Math.ceil(Math.max(...this.emgTime))

                
                for (const [key, value] of Object.entries(events)){
                    const start = parseFloat(value['start_s']);
                    const end = parseFloat(value['end_s']);
                    const startNorm = ((start - min) / (max-min)) * (300-0) + 0
                    const endNorm = ((end - min) / (max-min)) * (300-0) + 0
                    if(this.confirmedEvents[key] === true){
                        if(value.sensor === "both"){
                            markAreaDataMR.push([{ name: key, xAxis: startNorm*200}, { xAxis: endNorm*200}])
                            markAreaDataML.push([{ name: key, xAxis: startNorm*200}, { xAxis: endNorm*200}])
                        }
                        if(value.sensor === "MR"){
                            markAreaDataMR.push([{ name: key, xAxis: startNorm*200}, { xAxis: endNorm*200}])
                        }
                        if(value.sensor === "ML"){
                            markAreaDataML.push([{ name: key, xAxis: startNorm*200}, { xAxis: endNorm*200}])
                        }
                    }
                    
                }

            }
            let option;

            option = {
                legend: {
                    data: ['MR', 'ML'],
                    right: 10,
                    top: 60,
                    orient: 'vertical'
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: {
                        type: 'cross'
                    },
                    borderWidth: 1,
                    borderColor: '#ccc',
                    padding: 10,
                    textStyle: {
                        color: '#000'
                    },
                    position: function (pos, params, el, elRect, size) {
                        const obj = {
                            top: 10
                        };
                        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
                            return obj;
                    },
                    formatter: function (params) {
                        if (params !== undefined) {  
                            params.sort((a, b) => a.seriesIndex - b.seriesIndex);
                            let title = "";
                            let startEvent = null;
                            let endEvent = null;
                            //let eventMeanFreqMr = null;
                            //let eventMeanFreqMl = null;


                            //console.log("PARAMS: ", params)
                            let xPoint = parseFloat(params[0].axisValue);
                            let yPoint = params[0].value;
                            //console.log(this.tileIndex)
                            //let factor = this.tileIndex + 1.00
                            const formattedValue = yPoint.toFixed(2);
                            //console.log(stdMR)
                            
                            let currentStdMR = stdMR[params[0].dataIndex].toFixed(2);
                            let currentStdML = stdML[params[1].dataIndex].toFixed(2);
                            let currentHrvLfHf = hrvLfHf[params[0].dataIndex].toFixed(2);
                            let currentHrvMean =hrvMean[params[0].dataIndex].toFixed(2);
                            let currentHrvSdnn =hrvSdnn[params[0].dataIndex].toFixed(2);
                            let currentRri = rri[params[0].dataIndex].toFixed(2);
                            let currentFMeanMr = fMeanMr[params[0].dataIndex].toFixed(2);
                            let currentFMeanMl = fMeanMl[params[1].dataIndex].toFixed(2);


                            

                            if(Object.keys(events).length > 0){
                                for (const [key, value] of Object.entries(events)){
                                    //console.log(value['start_s'], value['end_s'])
                                    //console.log(xPoint, yPoint)
                                    if(value['start_s'] <= xPoint && value['end_s'] >= xPoint){
                                        title = "Event " + key.slice(1)
                                        console.log("dentro")
                                        startEvent = value['start_s']
                                        endEvent = value ['end_s']

                                        //eventMeanFreqMr = (value['mnf_mr']).toFixed(2);
                                        //eventMeanFreqMl = (value ['mnf_ml']).toFixed(2);

                                    }
                                }
                            }

                            // Return the tooltip HTML
                            return `
                                ${title ? `<strong>${title}</strong><br>Start: ${startEvent.toFixed(2)} s, End: ${endEvent.toFixed(2)} s<br>Duration: ${(endEvent-startEvent).toFixed(2)} s<hr>` : ''}
                                ${params[0].marker}  <b>MR</b> : ${formattedValue}<br>
                                MVC: ${mvcMR}<br>
                                SD: ${currentStdMR}<br>
                                Fmean: ${currentFMeanMr}<br>
                                <hr>
                                ${params[1].marker} <b>ML</b> : ${params[1].value.toFixed(2)}<br>
                                MVC: ${mvcML}<br>
                                SD: ${currentStdML}<br>
                                Fmean: ${currentFMeanMl}<br>
                                <hr>
                                <b> HRV metrics</b><br>
                                RRI: ${currentRri}<br>
                                LF / HF: ${currentHrvLfHf}<br>
                                Mean: ${currentHrvMean}<br>
                                SD: ${currentHrvSdnn}<br>
                                <!--LF/HF (5 min): <br>
                                Mean (5 min)<br>
                                SD (5 min): <br>
                                SD (Sleep cycle (90 min)): 6<br>
    
                                ${title ? `SD (5 s before & after event): 7<br>SD (during event): ` : ''}-->
                                <hr>
                                t: ${(parseFloat(params[0].axisValue)).toFixed(2)} s<br>
                                Sampling Rate: 200 Hz<br>
                            `;
                        }       
                    }
                },
                axisPointer: {
                    link: [
                    {
                        xAxisIndex: 'all'
                    }
                    ],
                    label: {
                        backgroundColor: '#777',
                        formatter: function (params) {
                            return parseFloat(params.value).toFixed(2); // Format the x-axis value to 2 decimal places
                        }
                    }
                },
                toolbox: {
                    feature: {
                        dataZoom: {
                            yAxisIndex: false,
                            icon: null
                        },
                        brush: {
                            type: ['lineX', 'clear'],
                            show: false
                        }
                    }
                },
                brush: {
                    type: ['lineX', 'clear'],
                    xAxisIndex: 'all', // Apply brush to all x-axes
                    yAxisIndex: 'all', // Apply brush to all y-axes
                    brushLink: [0,1],  // Link the selection to both series
                    seriesIndex: [0, 1], // Apply the brush to both series
                    outOfBrush: {
                        colorAlpha: 0.1
                    }
                },
                dataZoom: [
                    {
                        type: 'slider',
                        xAxisIndex: [0, 1], // Link both x-axes
                        bottom: 30, // Place the zoom slider close to the bottom of the page
                        height: 25, // Height of the zoom slider to keep it compact
                    },
                    {
                        type: 'inside',
                        xAxisIndex: [0, 1], // Link both x-axes
                        zoomOnMouseWheel: false,
                    }
                ],
                grid: [
                {
                    left: 90,  // Align the first chart from the left side
                    right: 70, // Align the first chart from the right side
                    top: 40,   // Provide some space from the top of the container
                    height: '35%',  // Set the height of the first chart as 35% of the available space
                },
                {
                    left: 90,  // Align the second chart from the left side
                    right: 70, // Align the second chart from the right side
                    top: '50%', // Start the second chart at the middle (50% of the height)
                    height: '35%', // Set the height of the second chart as 35% of the available space
                }
                ],
                xAxis: [
                    {
                    type: 'category',
                    data: this.emgTime,
                    gridIndex: 0,
                    name: 'Time (s)',
                    axisLabel: {
                        interval: (index) => {
                            // Only show every 25-second label on the x-axis
                            return index % (25 * 200) === 0;
                        },
                        },
                        axisTick: {
                        alignWithLabel: true,
                        },
                    },
                    {
                    type: 'category',
                    data: this.emgTime,
                    gridIndex: 1,
                    name: 'Time (s)',
                    axisLabel: {
                        interval: (index) => {
                            // Only show every 25-second label on the x-axis
                            return index % (25 * 200) === 0;
                        },
                        },
                        axisTick: {
                        alignWithLabel: true,
                        },
                    }
                ],
                yAxis: [
                    {
                        gridIndex: 0,
                        type: 'value',
                        name: 'Amplitude (V)',
                        max: Math.max(Math.ceil(this.maxAmplitudeMR), Math.ceil(this.maxAmplitudeML), this.mvcMR, this.mvcML),
                        yAxisIndex: 0,
                        scale: true,
                        splitArea: {
                            show: true
                        }
                    }, 
                    {
                        gridIndex: 1,
                        type: 'value',
                        name: 'Amplitude (V)',
                        max: Math.max(Math.ceil(this.maxAmplitudeMR), Math.ceil(this.maxAmplitudeML), this.mvcMR, this.mvcML),
                        scale: true,
                        splitArea: {
                            show: true
                        }
                    }
                ],
                series: [
                    {
                    name: 'MR',
                    type: 'line',
                    data: this.mr,
                    xAxisIndex:0,
                    yAxisIndex: 0,
                    showSymbol:false,
                    lineStyle: {
                        color: 'rgba(0, 0, 255, 0.6)' // Blue line with alpha
                    },
                    itemStyle: {
                        color: 'rgba(0, 0, 255, 0.6)' // Blue dot color with alpha for tooltips
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 255, 0.6)' // Tooltip background matching the line
                    },
                    markArea: {
                        itemStyle: {
                            color: 'rgba(133.4, 206.2, 97.4, 0.2)',  // Light purple with transparency
                            borderColor: 'rgb(133.4, 206.2, 97.4)',  // Border color of the mark area
                            borderWidth: 1,  // Border width
                        },
                        data: markAreaDataMR
                    },
                    markLine: {
                        data: [
                            {
                                yAxis: (this.thresholdMr*this.mvcMR/100).toFixed(2), // Set the threshold value here
                                label: {
                                    formatter: 'Threshold MR', // Customize label
                                    position: 'start', // Position label at the end of the line
                                },
                                lineStyle: {
                                    color: '#a942e9', // Slightly opaque line for visibility
                                    type: 'solid', // Change to 'dashed' if preferred
                                    width: 3
                                }
                            },
                            {
                                yAxis: this.mvcMR, // Set the threshold value here
                                label: {
                                    formatter: 'MVC MR', // Customize label
                                    position: 'start', // Position label at the end of the line
                                },
                                lineStyle: {
                                    color: 'rgba(255, 127, 80, 0.7)', // Customize line color
                                    type: 'dashed',
                                    width: 2
                                }
                            }
                        ]
                    }
                    },
                    {
                    name: 'ML',
                    type: 'line',
                    data: this.ml,
                    xAxisIndex:1,
                    yAxisIndex: 1,
                    showSymbol:false,
                    lineStyle: {
                        color: 'rgba(255, 0, 0, 0.6)' // Red line with alpha
                    },
                    itemStyle: {
                        color: 'rgba(255, 0, 0, 0.6)' // Red dot color with alpha for tooltips
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 0, 0, 0.6)' // Tooltip background matching the line
                    },
                    markArea: {
                        itemStyle: {
                            color: 'rgba(133.4, 206.2, 97.4, 0.2)',  // Light purple with transparency
                            borderColor: 'rgba(133.4, 206.2, 97.4)',  // Border color of the mark area
                            borderWidth: 1,  // Border width
                        },
                        data: markAreaDataML
                    },
                    markLine: {
                        data: [
                            {
                                yAxis: (this.thresholdMl*this.mvcML/100).toFixed(2), // Set the threshold value here
                                label: {
                                    formatter: 'Threshold ML', // Customize label
                                    position: 'start', // Position label at the end of the line
                                },
                                lineStyle: {
                                    color: '#a942e9', // Slightly opaque line for visibility
                                    type: 'solid', // Change to 'dashed' if preferred
                                    width: 3
                                }
                            }, {
                                yAxis: this.mvcML, // Set the threshold value here
                                label: {
                                    formatter: 'MVC ML', // Customize label
                                    position: 'start', // Position label at the end of the line
                                },
                                lineStyle: {
                                    color: 'rgba(255, 127, 80, 0.7)', // Customize line color
                                    type: 'dashed',
                                    width: 2
                                }
                            }
                        ]
                    }
                    },
                ]
                }
            
            this.emgChart.setOption(option);

            // Double-click to reset zoom
            this.emgChart.getZr().on('dblclick', (params) => {
                console.log(params);
                this.emgChart.dispatchAction({
                    type: 'dataZoom',
                    start: Math.min(...this.emgTime),
                    end: Math.max(...this.emgTime)
                });

                // Deactivate zoom mode on double-click
                //this.emgChart.dispatchAction({
                //    type: 'takeGlobalCursor',
                //    key: 'dataZoomSelect',
                //    dataZoomSelectActive: false
                //});
            });
            /*
            document.getElementById('edit-button').addEventListener('click', () => {
                if(this.selectionActive==true){
                    this.emgChart.dispatchAction({
                        type: 'takeGlobalCursor',
                        key: 'brush',
                        brushOption: {
                            brushType: 'lineX',
                            brushMode: 'single'
                        }
                    });
                } else {
                    this.emgChart.dispatchAction({
                        type: 'brush',
                        areas: []
                    });
                }
                
            });
            */

            this.emgChart.on('brushSelected', this.handleBrushSelection);
        },
        handleBrushSelection(params) {
            //this.selectionActive = true;
            const selected = params.batch[0];
            console.log("selected: ", selected)
            if (selected) {
                const { areas } = selected;
                
                if (areas.length === 0){
                    this.startSelection = null;
                    this.endSelection = null;
                } else {
                    console.log("areas[0]: ", areas[0])
                    console.log(this.emgTime[areas[0].coordRange[0]], this.emgTime[areas[0].coordRange[1]])
                    this.coords = areas[0].coordRange;

                    this.startSelection = this.emgTime[areas[0].coordRange[0]];
                    this.endSelection = this.emgTime[areas[0].coordRange[1]];
                }
            }
        },
        async updateThresholdMr(thresholdMr){
            console.log("thresholdMr: ", thresholdMr)
            console.log(typeof thresholdMr)
            
            const path = `http://127.0.0.1:5000/patient-threshold/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
            let payload= {};
            payload['sensor'] = "MR";
            payload['threshold'] = thresholdMr;

            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.post(path, payload, {headers})
                .then(() => {
                    console.log("emgChart: ", this.emgChart)
                    this.emgChart.setOption({
                        series: [{
                            name: 'MR',
                            markLine: {
                            data: [
                                {
                                    yAxis: (this.mvcMR*thresholdMr/100).toFixed(2), // Set the threshold value here
                                    label: {
                                        formatter: 'Threshold MR', // Customize label
                                        position: 'start', // Position label at the end of the line
                                    },
                                        lineStyle: {
                                        color: '#a942e9', // Slightly opaque line for visibility
                                        type: 'solid', // Change to 'dashed' if preferred
                                        width: 3
                                    }
                                }, {
                                        yAxis: this.mvcMR, // Set the threshold value here
                                        label: {
                                            formatter: 'MVC MR', // Customize label
                                            position: 'start', // Position label at the end of the line
                                        },
                                        lineStyle: {
                                            color: 'rgba(255, 127, 80, 0.7)', // Customize line color
                                            type: 'solid' // Customize line type (solid, dashed, dotted, etc.)
                                        }
                                    }
                            ]
                    }}]
                    }, false, false);

                })
                .catch(err=>{
                    console.log(err)
                })
        },
        async updateThresholdMl(thresholdMl){
            const path = `http://127.0.0.1:5000/patient-threshold/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`;
            let payload= {};
            payload['sensor'] = "ML";
            payload['threshold'] = thresholdMl;

            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            await axios.post(path, payload, {headers})
                .then(() => {
                    console.log("emgChart: ", this.emgChart)
                    this.emgChart.setOption({
                        series: [{
                            name: 'ML',
                            markLine: {
                            data: [
                                {
                                    yAxis: (this.mvcML*thresholdMl/100).toFixed(2), // Set the threshold value here
                                    label: {
                                        formatter: 'Threshold ML', // Customize label
                                        position: 'start', // Position label at the end of the line
                                    },
                                    lineStyle: {
                                        color: '#a942e9', // Slightly opaque line for visibility
                                        type: 'solid', // Change to 'dashed' if preferred
                                        width: 3
                                    }
                                },{
                                        yAxis: this.mvcML, // Set the threshold value here
                                        label: {
                                            formatter: 'MVC ML', // Customize label
                                            position: 'start', // Position label at the end of the line
                                        },
                                        lineStyle: {
                                            color: 'rgba(255, 127, 80, 0.7)', // Customize line color
                                            type: 'solid' // Customize line type (solid, dashed, dotted, etc.)
                                        }
                                    }
                            ]
                    }}]
                    }, false, false);
                })
                .catch(err=>{
                    console.log(err)
                })
        },
        generateHeatmapData(totalDurationInSeconds, events) {
            const cellsPerRow = 18;          // Number of cells in each row
            const cellDuration = 300;        // Each cell represents 5 minutes = 300 seconds (5 min * 60 s)

            // Total number of cells based on the total duration in seconds
            const totalCells = Math.ceil(totalDurationInSeconds / cellDuration);
            this.totalCells = totalCells-1;
            //let x = (parseFloat(totalCells)).toFixed(2)
            //let y = (parseFloat(this.tileIndex) +0.5).toFixed(2)
            //console.log(x, y)
            //console.log(y > x)
            const numRows = Math.ceil(totalCells / cellsPerRow); // Total number of rows needed
            //console.log(numRows);

            let heatmapData = [];

            // Initialize heatmap data with zeros
            for (let row = 0; row < numRows; row++) {
                for (let col = 0; col < cellsPerRow; col++) {
                    const cellIndex = row * cellsPerRow + col;

                    if (cellIndex >= totalCells) break; // Stop if we exceed the total number of cells

                    const value = 0;  // Default value
                    heatmapData.push([col, row, value]); // Note: Col (x) first, then Row (y)
                }
            }
            //console.log(events)
            if(Object.keys(events).length !== 0){
                //events = events.replace(/NaN/g, 'null');
                //events = JSON.parse(events)
                // Now we will check the events to populate the heatmap data
                for (const eventKey in events) {
                    //console.log("eventKey: ", eventKey)
                    const event = events[eventKey];
                    const start = event.start_s; // Start time of the event
                    const end = event.end_s;     // End time of the event

                    // Determine which cells the event falls into
                    for (let row = 0; row < numRows; row++) {
                        for (let col = 0; col < cellsPerRow; col++) {
                            const cellIndex = row * cellsPerRow + col;

                            if (cellIndex >= totalCells) break; // Stop if we exceed total cells

                            // Calculate the start and end times for the current cell
                            const cellStart = (col + (row * cellsPerRow)) * cellDuration; // Start time of the cell
                            const cellEnd = cellStart + cellDuration; // End time of the cell

                            // Check if the event falls within the cell's time range
                            if (start < cellEnd && end > cellStart) {
                                // Increment the value for the corresponding cell
                                //console.log("CIAOCIAO")
                                if(events[eventKey].confirmed === true){
                                    heatmapData[cellIndex][2] += 1; // Increment the value at index 2 (the value field)
                                }
                            }
                        }
                    }
                }
            }

            return { "HM": heatmapData, "rows": numRows }; // Return the heatmap data and number of rows
        },
        drawECHeatMap(){
            let chartInstance = markRaw(echarts.init(document.getElementById('ec-heatmap')));
            let option;
            const minutes = [
                5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90
            ];

            let heatMapData = this.generateHeatmapData(this.emgDataLengthS, this.predictions);
            let data = heatMapData["HM"]
            //console.log(heatMapData)
            let numRows = heatMapData["rows"]

            const sleepCycles = Array.from({length:numRows}, (_, i) => i + 1);

            //let data = [[0,0,0], [4, 0, 0], [2,1,0], [2,2,0], [3,1,0], [0, 1, 0], [1, 0, 0], [1,1, 0], [2, 0, 0], [3, 0, 0], [8, 8, 0], [5,4,3], [6, 2, 3], [14,4,2],[17, 0, 0], [15,1,0], [12,1,0], [7,1,0], [6,1,0], [5,1,0], [4,2,0], [4,0,0], [4,1,0], [4,3,0], [4,4,0], [0,4,0], [1,4,0], [2,4,0], [14,3,0], [15,3,0], [16,3,0]]
            //let selectedInterval = [[0,0,0]];


            option = {
                tooltip: {
                    position: 'top',
                    formatter: function (params) {
                        let fiveMinInterval = parseFloat(params.data[0])+(params.data[1]*18)
                        let cycle = parseInt(params.data[1])+1
                        return `<b>Cycle ${cycle}</b><br><b >Start (s)</b>: ${fiveMinInterval*60*5}<br><b>End (s)</b>: ${(fiveMinInterval*60*5)+(60*5)}`;
                    }
                },
                title: {
                    text: 'Number of events', // Add a title for the visual maps
                    right: '0%',  // Align it with the visual maps on the right
                    top: '0%',      // Position the title just above the visual maps
                    show: (Object.keys(this.predictions).length  > 0),
                    textStyle: {
                        fontSize: 12,
                        fontWeight: 'bold'
                    }
                },
                grid: {
                    //height: '50%',
                    //top: '4%',
                    top: 35,
                    left:50,
                    right:120,
                    bottom:35
                },
                xAxis: {
                    type: 'category',
                    name: "min",
                    data: minutes,
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    name:"Sleep cycle", 
                    data: sleepCycles,
                    inverse: true,
                    nameLocation: 'start',
                    show: true,
                    splitArea: {
                        show: true
                    }
                },
                visualMap: [{
                    type: 'continuous',
                    dimension: 2,
                    min: 0,
                    max: Math.max(...data.map(item => item[2])),
                    seriesIndex: 0,
                    text: ['high', 'low'],
                    calculable: (Object.keys(this.predictions).length  > 0),
                    show: (Object.keys(this.predictions).length  > 0),
                    orient: 'vertical', // Set orientation to vertical
                    right: '6%', // Position on the right side
                    top: '4%', // Adjust top to control vertical spacing
                },
                {
                    dimension: 2,
                    seriesIndex : 1,
                    calculable: false,
                    show: false,
                    inRange: {
                        color: []
                    }
                }],
                series: [
                    {
                    name: 'Intervals',
                    type: 'heatmap',
                    data: data,
                    seriesIndex: 0,
                    center: ["50%", "75%"],
                    label: {
                        show: true,
                        formatter: function (params) {
                            //console.log(params)
                            if(parseInt(params.data[2])>0){
                                return params.data[2]
                            } else {
                                return ``;
                            }
                            
                        }
                    },
                    itemStyle: {
                        borderColor: '#f4d79a',
                        borderType: 'solid',
                        borderWidth: 1,
                        show:false
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    },
                    {
                        type: 'heatmap',
                        data: this.selectedInterval,
                        seriesIndex: 1,
                        label: {
                            show: false
                        },
                        itemStyle: {
                            borderColor: 'black',
                            borderType: 'solid',
                            borderWidth: 2,
                            show:false
                        }
                    }
                ]
            };
            chartInstance.setOption(option);

            // Add a click event listener
            chartInstance.on('click', function(params) {
                console.log("clicked")
                this.selectedInterval = [];
                this.emgReceived = false;
                option.series[1].data = this.selectedInterval;
                chartInstance.setOption(option)
                console.log(params.data)
                this.selectedInterval.push(params.data)
                option.series[1].data = this.selectedInterval;
                chartInstance.setOption(option)
        
                console.log(this.selectedInterval)

                let fiveMinInterval = (params.data[0])+(params.data[1]*18)
                console.log(fiveMinInterval)
                this.tileIndex = fiveMinInterval.toFixed(2);
                this.getData(fiveMinInterval.toFixed(2));
            }.bind(this));


        },
        async getSsdData(){
            const path = `http://127.0.0.1:5000/ssd/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}/200`
            const headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log("ssd data")
                    console.log(res.data)
                    this.ssdData = res.data;
                    this.ssdDataReceived = true;

                })
                .catch(err=>{
                    console.log(err)
                })
    
        },
        isRem(entry){
            if(entry['stage'] === 'rem'){
                return entry['stage']
            }
        },
        isDeep(entry){
            if(entry['stage'] === 'deep'){
                return entry['stage']
            }
        },
        isLight(entry){
            if(entry['stage'] === 'light'){
                return entry['stage']
            }
        },
        getMax(arr, prop) {
            var max = 0;
            for (var i=0 ; i<arr.length ; i++) {
                if (parseInt(arr[i][prop]) > parseInt(max))
                    max = arr[i][prop];
            }
            return max;
        },
        async drawSSDHeatMap(){
            let chartInstance = markRaw(echarts.init(document.getElementById('ssd-heatmap')));
            let option;

            const minutes = [
                5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90
            ];            

            let maxY = this.getMax(this.ssdData, 'y');

            const sleepCycles = Array.from({length: maxY+1}, (_, i) => i + 1);

            console.log("sleep cycles: ", sleepCycles)

            let remData = this.ssdData.filter(this.isRem);
            let deepData = this.ssdData.filter(this.isDeep);
            let lightData = this.ssdData.filter(this.isLight);

            //let allData = this.ssdData.map(function (item) {
            //    return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            //})

            remData = remData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });

            deepData = deepData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });

            lightData = lightData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });
            /*
            if(JSON.stringify(this.selectedInterval) === JSON.stringify([[0,0,0]])){
                console.log("TRUEEEEEEEEE")
                // Function to find the item with x = 0 and y = 0
                 const findData = (dataArray) => dataArray.find(item => item[0] === 0 && item[1] === 0);

                // Look for the item in all three data arrays
                const remItem = findData(remData);
                const deepItem = findData(deepData);
                const lightItem = findData(lightData);

                // Check which item exists and set selectedInterval accordingly
                if (remItem) {
                    this.selectedInterval = [remItem]; // If found in remData
                } else if (deepItem) {
                    this.selectedInterval = [deepItem]; // If found in deepData
                } else if (lightItem) {
                    this.selectedInterval = [lightItem]; // If found in lightData
                }
                console.log(this.selectedInterval)
            }

            console.log("light data: ", lightData)
            */

            option = {
                tooltip: {
                    position: 'top',
                    formatter: function (params) {
                        //if (params.seriesIndex === 3) {
                        //    return ''; // Return empty for series 3 to exclude from tooltip
                        //}
                        let fiveMinInterval = parseFloat(params.data[0])+(params.data[1]*18)
                        let cycle = parseInt(params.data[1])+1
                        console.log(params)
                        console.log(params.value)
                        return `<b>Cycle ${cycle}</b><br><b>${(params.value[3]).toUpperCase()}</b><br />
                                ${params.marker}: ${params.value[4].toFixed(2)} (LF/HF) ± ${params.value[2]} (SD)<br>
                                <b>Start (s)</b>: ${fiveMinInterval*60*5}<br><b>End (s)</b>: ${(fiveMinInterval*60*5)+(60*5)}`;
                    }
                },
                title: {
                    text: 'Uncertainity level', // Add a title for the visual maps
                    right: '0%',  // Align it with the visual maps on the right
                    top: '0%',      // Position the title just above the visual maps
                    textStyle: {
                        fontSize: 14,
                        fontWeight: 'bold'
                    }
                },
                grid: {
                    //height: '50%',
                    top: 35,
                    left:50,
                    right:150,
                    bottom:35
                },
                xAxis: {
                    type: 'category',
                    name: "min",
                    data: minutes,
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    name:"Sleep cycle", 
                    data: sleepCycles,
                    inverse: true,
                    nameLocation: 'start',
                    show: true,
                    splitArea: {
                        show: true
                    }
                },
                /*
                visualMap: [
                {
                    type: 'continuous',
                    dimension: 2,
                    seriesIndex: 0,
                    min: Math.min(...remData.map(item => item[2])), // Min value of HRV_SDNN for NREM
                    max: Math.max(...remData.map(item => item[2])), // Max value of HRV_SDNN for NREM
                    inRange: {
                        color: ['#d916b9', '#dcabd4']
                    },
                    text: ["high uncertainty (high SD)", "low uncertainity (low SD)"],
                    outOfRange: {
                        color: 'transparent'
                    },
                    controller: {
                        inRange: { color: ['#d916b9', '#dcabd4'] }
                    },
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    //bottom: '24%',
                    bottom: '10%'
                },
                {
                    type: 'continuous',
                    dimension: 2,
                    seriesIndex: 1,
                    min: Math.min(...lightData.map(item => item[2])), // HRV_SDNN for REM
                    max: Math.max(...lightData.map(item => item[2])),
                    inRange: {
                        color: ['#12dada', '#b0d8d8'] // Blue scale for REM
                    },
                    outOfRange: {
                        color: 'transparent'
                    },
                    controller: {
                        inRange: { color: ['#12dada', '#b0d8d8'] }
                    },
                    text: ["high uncertainty (high SD)", "low uncertainity (low SD)"],
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    //bottom: '30%',
                    bottom: '20%'
                },
                {
                    type: 'continuous',
                    dimension: 2,
                    seriesIndex: 2,
                    min: Math.min(...deepData.map(item => item[2])), // HRV_SDNN for REM
                    max: Math.max(...deepData.map(item => item[2])),
                    inRange: {
                        color: ['#2b08b9', '#715fb8'] // Blue scale for REM
                    },
                    outOfRange: {
                        color: 'transparent'
                    },
                    controller: {
                        inRange: { color: ['#2b08b9','#715fb8'] }
                    },
                    text: ["high uncertainty (high SD)", "low uncertainity (low SD)"],
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    //bottom: '30%',
                    bottom:'30%'
                },
                {
                    dimension: 2,
                    seriesIndex : 3,
                    calculable: false,
                    show: false,
                    inRange: {
                        color: []
                    }
                }
                ],
                */
                visualMap: [
                    {
                        type: 'continuous',
                        dimension: 2,
                        seriesIndex: 0,
                        min: Math.min(...remData.map(item => item[2])), // Min value of HRV_SDNN for NREM
                        max: Math.max(...remData.map(item => item[2])), // Max value of HRV_SDNN for NREM
                        inRange: {
                            color: ['#d916b9', '#dcabd4'] // Purple scale
                        },
                        //text: ["high uncertainty (high SD)", "low uncertainty (low SD)"],
                        text: ["high", "low"],
                        outOfRange: {
                            color: 'transparent'
                        },
                        inverse: true,
                        calculable: true,
                        orient: 'vertical', // Set orientation to vertical
                        right: '0.5%', // Position on the right side
                        top: '4%', // Adjust top to control vertical spacing
                    },
                    {
                        type: 'continuous',
                        dimension: 2,
                        seriesIndex: 1,
                        min: Math.min(...lightData.map(item => item[2])), // Min value for REM
                        max: Math.max(...lightData.map(item => item[2])), // Max value for REM
                        inRange: {
                            color: ['#12dada', '#c7e5e5'] // Blue scale for REM
                        },
                        text: ["high", "low"],
                        outOfRange: {
                            color: 'transparent'
                        },
                        inverse: true,
                        calculable: true,
                        orient: 'vertical', // Set orientation to vertical
                        right: '14%', // Align it with the other visualMap
                        top: '4%', // Adjust top to create space below the first visualMap
                    },
                    {
                        type: 'continuous',
                        dimension: 2,
                        seriesIndex: 2,
                        min: Math.min(...deepData.map(item => item[2])), // Min value for Deep
                        max: Math.max(...deepData.map(item => item[2])), // Max value for Deep
                        inRange: {
                            color: ['#2b08b9', '#b1a8d8'] // Blue/purple scale for Deep
                        },
                        text: ["high", "low"],
                        outOfRange: {
                            color: 'transparent'
                        },
                        inverse: true,
                        calculable: true,
                        orient: 'vertical', // Set orientation to vertical
                        right: '7%', // Align it with the other visualMap
                        top: '4%', // Adjust top to create space below the second visualMap
                    },
                    {
                        dimension: 2,
                        seriesIndex: 3,
                        calculable: false,
                        show: false,
                        inRange: {
                            color: []
                        }
                    }
                ],


                series: [
                    {
                    name: 'REM data',
                    type: 'heatmap',
                    data: remData,
                    seriesIndex: 0,
                    label: {
                        show: true,
                        formatter: function () {
                            return 'R';
                        },
                        color: '#FFFFFF'
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    },
                    {
                    name: 'Light data',
                    type: 'heatmap',
                    data: lightData,
                    seriesIndex: 1,
                    label: {
                        show: true,
                        formatter: function () {
                            return 'L';
                        },
                        color: '#FFFFFF'
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    }, 
                    {
                    name: 'Deep data',
                    type: 'heatmap',
                    data: deepData,
                    seriesIndex: 2,
                    label: {
                        show: true,
                        formatter: function () {
                            return 'D';
                        },
                        color: '#FFFFFF'
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    },
                    {
                        type: 'heatmap',
                        data: this.selectedInterval,
                        tooltip: {
                            show: false
                        },
                        seriesIndex: 3,
                        label: {
                            show: false
                        },
                        itemStyle: {
                            borderColor: 'white',
                            borderType: 'solid',
                            borderWidth: 2,
                            show:false
                        }
                    }
                ]
            };
            chartInstance.setOption(option);
            console.log("option series: ", option.series)
            // Add a click event listener
            chartInstance.on('click', function(params) {
                console.log("clicked");
                
                // Reset selectedInterval to a new empty array
                this.selectedInterval = [];  
                this.emgReceived = false;

                // Format the clicked data properly
                const hrvSdnn = Math.round(params.data[2]); // Get HRV_SDNN
                const hrvLfhf = params.data[4]; // Get HRV_LFHF
                const stage = params.data[3]; // Get Stage

                // Push formatted data into selectedInterval
                this.selectedInterval.push([
                    params.data[0], // x value
                    params.data[1], // y value
                    hrvSdnn,        // HRV_SDNN
                    stage,          // Stage
                    hrvLfhf        // HRV_LFHF
                ]);

                // Update series 3 with selectedInterval data
                option.series[3].data = this.selectedInterval;

                // Set the option once after updating the data
                chartInstance.setOption(option);

                console.log("SELECTED INTERVAL", this.selectedInterval);

                // Calculate the five-minute interval
                let fiveMinInterval = (params.data[0]) + (params.data[1] * 18);
                console.log(fiveMinInterval);
                this.tileIndex = fiveMinInterval.toFixed(2);
                console.log("tile Index: ", this.tileIndex);

                // Call getData with the five-minute interval
                this.getData(fiveMinInterval.toFixed(2));
            }.bind(this));
        }
    }
  };
  </script>

<style>
.centered-column {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  margin-top: 0; /* Remove any top margin */
  padding-top: 0; /* Remove padding at the top */
}

.image-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 0; /* Ensure no additional margin */
}

.selected-image-container {
  margin-top: 0px; /* Minimal margin between image and selector */
}

#ec-heatmap, #ssd-heatmap {
  width: 100%;
  max-width: 600px;
  height: 240px;
  margin-top: 10px; /* Minimal margin */
}
</style>