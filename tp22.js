module.exports = function (RED) {
    "use strict";

    // #22 RTD Temperature Meter

    var TpCommon = require('./tpCommon');

    function TP_22Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp22", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput(function (msg, payload) {
            try {
                msg.payload = parseFloat(payload);
            } catch (e) {
                msg.payload = null;
            }
            node.send(msg);
        });

    }
    RED.nodes.registerType("Tibbit-#22", TP_22Node);
}

