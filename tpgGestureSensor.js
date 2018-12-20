module.exports = function (RED) {
    "use strict";

    // TP Grove - Gesture Sensor

    var TpCommon = require('./tpCommon');

    function TPG_GestureSensor_InNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tpgGestureSensor", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = payload;
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });
    }
    RED.nodes.registerType("GestureSensor", TPG_GestureSensor_InNode);
}
