module.exports = function (RED) {
    "use strict";

    // #26 IR code processor

    var TpCommon = require('./tpCommon');

    function TP_26Node(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp26", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

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
    RED.nodes.registerType("Tibbit-#26", TP_26Node);

}

