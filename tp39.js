module.exports = function (RED) {
    "use strict";

    // #39 LED

    var TpCommon = require('./tpCommon');

    function TP_39_OutNode(config) {
        RED.nodes.createNode(this, config);

        // config
        var node = this;
        this.config = config;

        // common
        var tc = new TpCommon("tp39_out", node);

        // Launch python
        tc.execPy([config.tpSlot, config.host]);

        // On Node Input
        tc.onInput(function (msg) {

            return msg.payload;
        });

        // On Node Output
        tc.onOutput();

    }
    RED.nodes.registerType("Tibbit-#39 out", TP_39_OutNode);
}
