module.exports = function (RED) {
    "use strict";

    // #54 Four dry contact inputs

    var TpCommon = require('./tpCommon');

    function TP_54Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common 
        var tc = new TpCommon("tp54", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {

            try {
                msg.payload = JSON.parse(payload);
            } catch(e) {
                msg.payload = null;
            }
            node.send(msg);

        });
    }
    RED.nodes.registerType("Tibbit-#54", TP_54Node);

    function TP_54_InNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp54_in", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Output
        tc.onOutput(function (msg, payload) {

            try {
                msg.payload = JSON.parse(payload);
            } catch(e) {
                msg.payload = null;
            }
            node.send(msg);

        });

    }
    RED.nodes.registerType("Tibbit-#54 in", TP_54_InNode);
}
