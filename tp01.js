module.exports = function (RED) {
    "use strict";

    // #01 Four-line RS232 port

    var TpCommon = require('./tpCommon');

    function TP_01_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp01_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("Tibbit-#01 out", TP_01_OutNode);

    function TP_01_InNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp01_in", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = Buffer.from(JSON.parse(payload));
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);

        });
    }
    RED.nodes.registerType("Tibbit-#01 in", TP_01_InNode);
}

