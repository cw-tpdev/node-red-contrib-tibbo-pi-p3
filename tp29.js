module.exports = function (RED) {
    "use strict";

    // #29 Ambient temperature meter

    var TpCommon = require('./tpCommon');

    function TP_29Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp29", node);

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
    RED.nodes.registerType("Tibbit-#29", TP_29Node);
}

