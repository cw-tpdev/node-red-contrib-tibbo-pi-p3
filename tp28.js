module.exports = function (RED) {
    "use strict";

    // #28 Ambient light sensor

    var TpCommon = require('./tpCommon');

    function TP_28Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp28", node);

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
    RED.nodes.registerType("Tibbit-#28", TP_28Node);
}

