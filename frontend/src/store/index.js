import { createStore } from 'vuex';
import VuexPersistence from 'vuex-persist';
import localForage from 'localforage';
import {clone} from 'pouchdb-utils';

const vuexLocal = new VuexPersistence({
  storage: localForage,
  asyncStorage: true,
  reducer: (state) => clone(state),
});


const store = createStore({
  state () {
    return {
      patientId: 0,
      weekId: '',
      file: '',
      fileSize: 0.0,
      userType: '',
      settingsSaved: false
    }
  },
  mutations: {
    /*
    setHighlightRange(state, range) {
      state.highlightRange = range;
    },
    */
    setUserType(state, userType) {
      state.userType = userType;
    },
    setSettingsSaved(state, settingsSaved){
      state.settingsSaved= settingsSaved;
    },
    setPatientId(state, patientId){
      state.patientId = patientId;
    },
    setWeekId(state, weekId){
      state.weekId = weekId;
    },
    setFile(state, file){
      state.file = file;
    },
    setFileSize(state, fileSize){
      state.fileSize = fileSize;
    }
  },
  plugins: [vuexLocal.plugin],

})

export default store;
