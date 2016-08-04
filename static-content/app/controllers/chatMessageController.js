myApp.controller('chatMessageCtrl', ['$scope', '$rootScope', '$resource', function ($scope, $rootScope, $resource) {

    $rootScope.$on("chatting", function () {
        document.getElementById('chat-message-input').placeholder = "Enter a message and save humanity";
    });
    $rootScope.$on("not chatting", function () {
        document.getElementById('chat-message-input').value = null;
        document.getElementById('chat-message-input').placeholder = "Save your brains, enter your user name";
    });

    $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + DEFAULT_CHANNEL_NAME);
    $scope.MessagesResource = $resource(API_ENDPOINT + "/message");
    $scope.lastTalking = new Date;

    $rootScope.$on('channelChanged', function (event, new_channel) {
        $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + new_channel);
    });

    $scope.chatMessageKeyPressed = function (keyEvent) {
        if ((keyEvent.which === 13) && (!$scope.posting)) {
            $scope.posting = true;
            var message_text = $scope.chatMessage;
            $scope.chatMessage = null;
            console.log('Sending Message: ' + $scope.chatMessage);
            
            var message = {
                // encodeURIComponent() doesn't encode single quotes, which are a problem
                // for API Gateway.
                channel: $rootScope.channel,
                participant: $rootScope.userName,
                message: message_text
            };
            console.log(message);

            $scope.MessagesResource.save(message, function (response) {
                $scope.chatMessage = null;
                $scope.posting = false;
                document.getElementById("chat-message-input").focus();
                $rootScope.$emit('serverMessage', response.server_messages);
            });
        } else {
            var diff = Date.now() - $scope.lastTalking;
            console.log(diff);

            // send talking update at a maximum rate
            if (diff < 1000) {
                return;
            }

            var message = {
                channel: $rootScope.channel,
                participant: $rootScope.userName
            };

            console.log('Posting to talkers.');
            $scope.TalkersResource.save(message, function () {
                $scope.lastTalking = new Date;
            });
        }
    };

}]);
